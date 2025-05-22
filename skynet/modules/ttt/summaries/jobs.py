import asyncio
import os
import time

from skynet.constants import ERROR_JOBS_KEY, PENDING_JOBS_KEY, RUNNING_JOBS_KEY
from skynet.env import enable_batching, job_timeout, max_concurrency, modules, redis_exp_seconds, use_vllm
from skynet.logs import get_logger
from skynet.modules.monitoring import (
    OPENAI_API_RESTART_COUNTER,
    SUMMARY_DURATION_METRIC,
    SUMMARY_ERROR_COUNTER,
    SUMMARY_FULL_DURATION_METRIC,
    SUMMARY_INPUT_LENGTH_METRIC,
    SUMMARY_QUEUE_SIZE_METRIC,
    SUMMARY_TIME_IN_QUEUE_METRIC,
)
from skynet.modules.ttt.llm_selector import LLMSelector
from skynet.modules.ttt.openai_api.app import is_ready as is_openai_api_ready
from skynet.modules.ttt.processor import process

from ..persistence import db
from .v1.models import DocumentMetadata, DocumentPayload, Job, JobId, JobStatus, JobType, Priority, Processors

log = get_logger(__name__)

TIME_BETWEEN_JOBS_CHECK = 0.3
TIME_BETWEEN_JOBS_CHECK_ON_ERROR = 10

background_task = None
current_tasks = set[asyncio.Task]()


def restart():
    log.info('Restarting Skynet...')

    OPENAI_API_RESTART_COUNTER.inc()

    # Rely on the supervisor to restart the process.
    # TODO: consider just restarting the vllm subprocess.
    os._exit(1)


def can_run_next_job() -> bool:
    if 'summaries:executor' not in modules:
        return False

    if enable_batching:
        return len(current_tasks) < max_concurrency

    return len(current_tasks) == 0


async def update_summary_queue_metric() -> None:
    """Update the queue size metric."""

    queue_size = await db.llen(PENDING_JOBS_KEY)
    SUMMARY_QUEUE_SIZE_METRIC.set(queue_size)


async def restore_stale_jobs() -> list[Job]:
    """Check if any jobs were running on disconnected workers and requeue them."""

    running_jobs_keys = await db.lrange(RUNNING_JOBS_KEY, 0, -1)
    running_jobs = await db.mget(running_jobs_keys)
    connected_clients = await db.client_list()
    stale_jobs = []

    for job_json in running_jobs:
        job = Job.model_validate_json(job_json)

        if str(job.worker_id) not in [client['id'] for client in connected_clients]:
            stale_jobs.append(job)

    if stale_jobs:
        ids = [job.id for job in stale_jobs]
        log.info(f"Restoring stale job(s): {ids}")
        await db.lpush(PENDING_JOBS_KEY, *[job.id for job in stale_jobs])
        await update_summary_queue_metric()


async def create_job(job_type: JobType, payload: DocumentPayload, metadata: DocumentMetadata) -> JobId:
    """Create a job and add it to the db queue if it can't be started immediately."""

    job = Job(payload=payload, type=job_type, metadata=metadata)
    processor = LLMSelector.get_job_processor(metadata.customer_id)

    # encode the processor in the job id to avoid having to retrieve the whole job object
    job.id += f':{processor.value}'
    job_id = job.id

    await db.set(job_id, Job.model_dump_json(job))

    log.info(f"Created job {job.id}.")

    if payload.priority == Priority.HIGH:
        await db.lpush(PENDING_JOBS_KEY, job_id)
    else:
        await db.rpush(PENDING_JOBS_KEY, job_id)

    await update_summary_queue_metric()

    return JobId(id=job_id)


async def get_job(job_id: str) -> Job:
    job_json = await db.get(job_id)
    job = Job.model_validate_json(job_json) if job_json else None

    return job


async def update_job(job_id: str, expires: int = None, **kwargs) -> Job:
    """Update a job in the db."""
    job_json = await db.get(job_id)

    # deserialize and merge
    job = Job(**(Job.model_validate_json(job_json).model_dump() | kwargs))

    # serialize changes and save to db
    await db.set(job_id, Job.model_dump_json(job), expires)

    return job


async def run_job(job: Job) -> None:
    exit_task = asyncio.create_task(restart_on_timeout(job))

    try:
        await _run_job(job)
    finally:
        exit_task.cancel()


async def update_done_job(job: Job, result: str, processor: Processors, has_failed: bool = False) -> None:
    should_expire = not has_failed or processor != Processors.LOCAL
    status = JobStatus.ERROR if has_failed else JobStatus.SUCCESS
    customer_id = job.metadata.customer_id

    updated_job = await update_job(
        expires=redis_exp_seconds if should_expire else None,
        job_id=job.id,
        end=time.time(),
        status=status,
        result=result,
    )

    if not should_expire:
        await db.rpush(ERROR_JOBS_KEY, job.id)
        SUMMARY_ERROR_COUNTER.inc()

    await db.lrem(RUNNING_JOBS_KEY, 0, job.id)

    SUMMARY_DURATION_METRIC.labels(updated_job.metadata.app_id, processor.value, customer_id).observe(
        updated_job.computed_duration
    )
    SUMMARY_FULL_DURATION_METRIC.observe(updated_job.computed_full_duration)
    SUMMARY_INPUT_LENGTH_METRIC.observe(len(updated_job.payload.text))

    log.info(
        f"Job {updated_job.id} duration: {updated_job.computed_duration}s full duration: {updated_job.computed_full_duration}s"
    )


async def _run_job(job: Job) -> None:
    has_failed = False
    result = None
    worker_id = await db.db.client_id()
    start = time.time()
    customer_id = job.metadata.customer_id

    SUMMARY_TIME_IN_QUEUE_METRIC.observe(start - job.created)

    log.info(f"Running job {job.id}. Queue time: {round(start - job.created, 3)} seconds")

    job = await update_job(job_id=job.id, start=start, status=JobStatus.RUNNING, worker_id=worker_id)

    # add to running jobs list if not already there (which may occur on multiple worker disconnects while running the same job)
    if job.id not in await db.lrange(RUNNING_JOBS_KEY, 0, -1):
        await db.rpush(RUNNING_JOBS_KEY, job.id)

    try:
        result = await process(job)
    except Exception as e:
        has_failed = True
        result = str(e)

    processor = LLMSelector.get_job_processor(customer_id, job.id)
    await update_done_job(job, result, processor, has_failed)

    # error returned from the api when vllm crashes with torch.OutOfMemoryError
    if result == 'Error code: 500' and processor == Processors.LOCAL:
        restart()


def create_run_job_task(job: Job) -> asyncio.Task:
    task = asyncio.create_task(run_job(job))
    task.add_done_callback(lambda t: current_tasks.discard(t))
    current_tasks.add(task)


async def maybe_run_next_job() -> None:
    if not can_run_next_job():
        return

    next_job_id = None

    if use_vllm:
        pending_jobs_keys = await db.lrange(PENDING_JOBS_KEY, 0, -1)

        for job_id in pending_jobs_keys:
            if job_id.endswith(Processors.LOCAL.value):
                next_job_id = job_id
                await db.lrem(PENDING_JOBS_KEY, 0, job_id)

                break

    if not next_job_id:
        next_job_id = await db.lpop(PENDING_JOBS_KEY)

    await update_summary_queue_metric()

    if next_job_id:
        log.info(f"Next job id: {next_job_id}")

        next_job = await get_job(next_job_id)
        create_run_job_task(next_job)


async def monitor_candidate_jobs() -> None:
    await restore_stale_jobs()

    while not await is_openai_api_ready():
        await asyncio.sleep(TIME_BETWEEN_JOBS_CHECK)

    while True:
        try:
            await maybe_run_next_job()
            await asyncio.sleep(TIME_BETWEEN_JOBS_CHECK)
        except Exception as e:
            log.error(f"Error in job monitoring: {e}")
            await asyncio.sleep(TIME_BETWEEN_JOBS_CHECK_ON_ERROR)


async def restart_on_timeout(job: Job) -> None:
    await asyncio.sleep(job_timeout)

    log.warning(f"Job {job.id} timed out after {job_timeout} seconds")

    customer_id = job.metadata.customer_id
    processor = LLMSelector.get_job_processor(customer_id, job.id)

    await update_done_job(job, "Job timed out", processor, has_failed=True)

    if processor == Processors.LOCAL:
        restart()


def start_monitoring_jobs() -> None:
    global background_task
    background_task = asyncio.create_task(monitor_candidate_jobs())
