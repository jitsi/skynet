import asyncio
import os
import time

from skynet.constants import (
    ERROR_JOBS_AZURE_KEY,
    ERROR_JOBS_LOCAL_KEY,
    ERROR_JOBS_OCI_KEY,
    ERROR_JOBS_OPENAI_KEY,
    PENDING_JOBS_AZURE_KEY,
    PENDING_JOBS_LOCAL_KEY,
    PENDING_JOBS_OCI_KEY,
    PENDING_JOBS_OPENAI_KEY,
    RUNNING_JOBS_AZURE_KEY,
    RUNNING_JOBS_LOCAL_KEY,
    RUNNING_JOBS_OCI_KEY,
    RUNNING_JOBS_OPENAI_KEY,
)
from skynet.env import (
    job_timeout,
    max_concurrency,
    max_concurrency_azure,
    max_concurrency_local,
    max_concurrency_oci,
    max_concurrency_openai,
    modules,
    redis_exp_seconds,
)
from skynet.logs import get_logger
from skynet.modules.monitoring import (
    OPENAI_API_RESTART_COUNTER,
    SUMMARY_CURRENT_TASKS_METRIC,
    SUMMARY_DURATION_METRIC,
    SUMMARY_ERROR_COUNTER,
    SUMMARY_FULL_DURATION_METRIC,
    SUMMARY_INPUT_LENGTH_METRIC,
    SUMMARY_QUEUE_SIZE_BY_PROCESSOR_METRIC,
    SUMMARY_QUEUE_SIZE_METRIC,
    SUMMARY_TIME_IN_QUEUE_METRIC,
)
from skynet.modules.ttt.llm_selector import LLMSelector
from skynet.modules.ttt.openai_api.app import is_ready as is_openai_api_ready
from skynet.modules.ttt.processor import process

from ..persistence import db
from .v1.models import DocumentMetadata, DocumentPayload, Job, JobId, JobStatus, JobType, Priority, Processors

log = get_logger(__name__)

TIME_BETWEEN_JOBS_CHECK = 1
TIME_BETWEEN_JOBS_CHECK_ON_ERROR = 10

background_task = None

# Per-processor task tracking
current_tasks = {
    Processors.OPENAI: set[asyncio.Task](),
    Processors.AZURE: set[asyncio.Task](),
    Processors.OCI: set[asyncio.Task](),
    Processors.LOCAL: set[asyncio.Task](),
}


def restart():
    log.info('Restarting Skynet...')

    OPENAI_API_RESTART_COUNTER.inc()

    # Rely on the supervisor to restart the process.
    # TODO: consider just restarting the vllm subprocess.
    os._exit(1)


def get_all_processor_queue_keys() -> dict[Processors, tuple[str, str, str]]:
    """Get queue keys for all processors: (pending_key, running_key, error_key)."""
    return {
        Processors.OPENAI: (PENDING_JOBS_OPENAI_KEY, RUNNING_JOBS_OPENAI_KEY, ERROR_JOBS_OPENAI_KEY),
        Processors.AZURE: (PENDING_JOBS_AZURE_KEY, RUNNING_JOBS_AZURE_KEY, ERROR_JOBS_AZURE_KEY),
        Processors.OCI: (PENDING_JOBS_OCI_KEY, RUNNING_JOBS_OCI_KEY, ERROR_JOBS_OCI_KEY),
        Processors.LOCAL: (PENDING_JOBS_LOCAL_KEY, RUNNING_JOBS_LOCAL_KEY, ERROR_JOBS_LOCAL_KEY),
    }


def get_processor_queue_keys(processor: Processors) -> tuple[str, str, str]:
    """Get the pending, running, and error queue keys for a specific processor."""
    return get_all_processor_queue_keys()[processor]


def get_processor_max_concurrency(processor: Processors) -> int:
    """Get the maximum concurrency limit for a specific processor."""
    concurrency_map = {
        Processors.OPENAI: max_concurrency_openai,
        Processors.AZURE: max_concurrency_azure,
        Processors.OCI: max_concurrency_oci,
        Processors.LOCAL: max_concurrency_local,
    }
    return concurrency_map.get(processor, max_concurrency)


def can_run_next_job(processor: Processors) -> bool:
    """Check if we can run a new job for the specified processor."""
    if 'summaries:executor' not in modules:
        return False

    current_processor_tasks = len(current_tasks[processor])
    max_processor_concurrency = get_processor_max_concurrency(processor)

    return current_processor_tasks < max_processor_concurrency


async def update_summary_queue_metric() -> None:
    """Update the queue size metric with combined queue sizes from all processors."""

    total_queue_size = 0

    # Sum up queue sizes from all processor-specific queues
    for processor in get_all_processor_queue_keys():
        pending_key = get_processor_queue_keys(processor)[0]
        processor_queue_size = await db.llen(pending_key)
        total_queue_size += processor_queue_size

        # Set individual processor queue size metric
        SUMMARY_QUEUE_SIZE_BY_PROCESSOR_METRIC.labels(processor=processor.value).set(processor_queue_size)

    SUMMARY_QUEUE_SIZE_METRIC.set(total_queue_size)


def update_current_tasks_metrics() -> None:
    """Update the current tasks metrics for all processors."""
    for processor in get_all_processor_queue_keys():
        current_task_count = len(current_tasks[processor])
        SUMMARY_CURRENT_TASKS_METRIC.labels(processor=processor.value).set(current_task_count)


async def migrate_legacy_queues() -> None:
    """Migrate jobs from legacy single queues to processor-specific queues."""

    # Legacy queue keys - these may still contain jobs from before the migration
    legacy_pending_key = 'jobs:pending'
    legacy_running_key = 'jobs:running'
    legacy_error_key = 'jobs:error'

    migrated_count = 0

    # Migrate pending jobs
    while True:
        job_id = await db.lpop(legacy_pending_key)
        if not job_id:
            break

        job_json = await db.get(job_id)
        if not job_json:
            continue

        try:
            job = Job.model_validate_json(job_json)
            processor = LLMSelector.get_job_processor(job.metadata.customer_id, job_id)
            pending_key = get_processor_queue_keys(processor)[0]

            # Maintain job priority - high priority jobs go to front
            if job.payload.priority == Priority.HIGH:
                await db.lpush(pending_key, job_id)
            else:
                await db.rpush(pending_key, job_id)

            migrated_count += 1
            log.info(f"Migrated pending job {job_id} to {processor.value} queue")

        except Exception as e:
            log.error(f"Failed to migrate pending job {job_id}: {e}")

    # Migrate running jobs
    running_job_ids = await db.lrange(legacy_running_key, 0, -1)
    for job_id in running_job_ids:
        job_json = await db.get(job_id)
        if not job_json:
            continue

        try:
            job = Job.model_validate_json(job_json)
            processor = LLMSelector.get_job_processor(job.metadata.customer_id, job_id)
            _, running_key, _ = get_processor_queue_keys(processor)

            await db.rpush(running_key, job_id)
            await db.lrem(legacy_running_key, 0, job_id)
            migrated_count += 1
            log.info(f"Migrated running job {job_id} to {processor.value} running queue")

        except Exception as e:
            log.error(f"Failed to migrate running job {job_id}: {e}")

    # Migrate error jobs
    error_job_ids = await db.lrange(legacy_error_key, 0, -1)
    for job_id in error_job_ids:
        job_json = await db.get(job_id)
        if not job_json:
            continue

        try:
            job = Job.model_validate_json(job_json)
            processor = LLMSelector.get_job_processor(job.metadata.customer_id, job_id)
            _, _, error_key = get_processor_queue_keys(processor)

            await db.rpush(error_key, job_id)
            await db.lrem(legacy_error_key, 0, job_id)
            migrated_count += 1
            log.info(f"Migrated error job {job_id} to {processor.value} error queue")

        except Exception as e:
            log.error(f"Failed to migrate error job {job_id}: {e}")

    if migrated_count > 0:
        log.info(f"Migration completed: moved {migrated_count} jobs from legacy queues to processor-specific queues")
        await update_summary_queue_metric()


async def restore_stale_jobs() -> list[Job]:
    """Check if any jobs were running on disconnected workers and requeue them to processor-specific queues."""

    connected_clients = await db.client_list()
    all_stale_jobs = []

    # Check all processor-specific running job lists
    for processor in get_all_processor_queue_keys():
        _, running_key, _ = get_processor_queue_keys(processor)

        running_jobs_keys = await db.lrange(running_key, 0, -1)
        if not running_jobs_keys:
            continue

        running_jobs = await db.mget(running_jobs_keys)

        for job_json in running_jobs:
            if not job_json:
                continue

            job = Job.model_validate_json(job_json)

            if str(job.worker_id) not in [client['id'] for client in connected_clients]:
                all_stale_jobs.append((job, processor))

    if all_stale_jobs:
        ids = [job.id for job, _ in all_stale_jobs]
        log.info(f"Restoring stale job(s): {ids}")

        # Restore each job to its appropriate processor queue
        for job, processor in all_stale_jobs:
            pending_key = get_processor_queue_keys(processor)[0]
            await db.lpush(pending_key, job.id)

        await update_summary_queue_metric()

    return [job for job, _ in all_stale_jobs]


async def create_job(job_type: JobType, payload: DocumentPayload, metadata: DocumentMetadata) -> JobId:
    """Create a job and add it to the processor-specific queue."""

    job = Job(payload=payload, type=job_type, metadata=metadata)
    processor = LLMSelector.get_job_processor(metadata.customer_id)

    # encode the processor in the job id to avoid having to retrieve the whole job object
    job.id += f':{processor.value}'
    job_id = job.id

    await db.set(job_id, Job.model_dump_json(job))

    log.info(f"Created job {job.id} for processor {processor.value}.")

    # Route to processor-specific queue
    pending_key = get_processor_queue_keys(processor)[0]

    if payload.priority == Priority.HIGH:
        await db.lpush(pending_key, job_id)
    else:
        await db.rpush(pending_key, job_id)

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

    # Use processor-specific error queue
    if not should_expire:
        _, _, error_key = get_processor_queue_keys(processor)
        await db.rpush(error_key, job.id)
        SUMMARY_ERROR_COUNTER.inc()

    # Remove from processor-specific running queue
    _, running_key, _ = get_processor_queue_keys(processor)
    await db.lrem(running_key, 0, job.id)

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

    # Add to processor-specific running jobs list if not already there
    processor = LLMSelector.get_job_processor(customer_id, job.id)
    _, running_key, _ = get_processor_queue_keys(processor)

    if job.id not in await db.lrange(running_key, 0, -1):
        await db.rpush(running_key, job.id)

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
    # Extract processor from job id
    processor_str = job.id.split(':')[-1]
    processor = Processors(processor_str)

    task = asyncio.create_task(run_job(job))

    def remove_task(t):
        current_tasks[processor].discard(t)
        # Update metrics when task is removed
        update_current_tasks_metrics()

    task.add_done_callback(remove_task)
    current_tasks[processor].add(task)

    # Update metrics when task is added
    update_current_tasks_metrics()

    return task


async def maybe_run_next_job() -> None:
    next_job_id = None

    # Priority order for processor queues - prefer faster external APIs over local processing
    processor_priority = [Processors.OCI, Processors.OPENAI, Processors.AZURE, Processors.LOCAL]

    # Try each processor queue in priority order, but only if it can handle more jobs
    for processor in processor_priority:
        if not can_run_next_job(processor):
            continue

        pending_key = get_processor_queue_keys(processor)[0]
        next_job_id = await db.lpop(pending_key)

        if next_job_id:
            log.info(f"Found job {next_job_id} in {processor.value} queue")
            break

    await update_summary_queue_metric()

    if next_job_id:
        log.info(f"Next job id: {next_job_id}")
        next_job = await get_job(next_job_id)
        create_run_job_task(next_job)


async def monitor_candidate_jobs() -> None:
    # Run one-time migration from legacy queues to processor-specific queues
    await migrate_legacy_queues()

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
