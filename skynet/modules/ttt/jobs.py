import asyncio
import timeit
import uuid
from skynet.logs import get_logger

from skynet.models.v1.document import DocumentPayload
from skynet.models.v1.job import Job, JobId, JobStatus, JobType
from skynet.modules.persistence import db
from skynet.modules.ttt.summaries import SummariesChain
from skynet.env import redis_exp_seconds

log = get_logger('skynet.jobs')

summary_api = SummariesChain()

TIME_BETWEEN_JOBS_CHECK = 10
PENDING_JOBS_KEY = "jobs:pending"
RUNNING_JOBS_KEY = "jobs:running"

background_task = None
current_task = None

def can_run_next_job() -> bool:
    return current_task is None or current_task.done()

async def restore_stale_jobs() -> list[Job]:
    """Check if any jobs were running on disconnected workers and requeue them."""

    running_jobs_keys = await db.lrange(RUNNING_JOBS_KEY, 0, -1)
    running_jobs = await db.mget(running_jobs_keys)
    connected_clients = await db.db.client_list()
    stale_jobs = []

    for job_json in running_jobs:
        job = Job.model_validate_json(job_json)

        if job.worker_id not in [client['id'] for client in connected_clients]:
            stale_jobs.append(job)

    if stale_jobs:
        ids = [job.id for job in stale_jobs]
        log.info(f"Restoring stale job(s): {ids}")
        await db.lpush(PENDING_JOBS_KEY, *[job.id for job in stale_jobs])

async def create_job(job_type: JobType, payload: DocumentPayload) -> JobId:
    """Create a job and add it to the db queue if it can't be started immediately."""

    job_id = str(uuid.uuid4())

    job = Job(
        id=job_id,
        payload=payload,
        type=job_type
    )

    await db.set(id, Job.model_dump_json(job))

    if can_run_next_job():
        create_run_job_task(job)
    else:
        await db.rpush(PENDING_JOBS_KEY, id)

    return JobId(id=id)

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
    await db.set(id, Job.model_dump_json(job), expires)

    return job

async def run_job(job: Job) -> None:
    log.info(f"Running job {job.id}")

    has_failed = False
    result = None
    worker_id = await db.db.client_id()

    await update_job(
        job_id=job.id,
        start=timeit.default_timer(),
        status=JobStatus.RUNNING,
        worker_id=worker_id)

    # add to running jobs list if not already there (which may occur on multiple worker disconnects while running the same job)
    if job.id not in await db.lrange(RUNNING_JOBS_KEY, 0, -1):
        await db.rpush(RUNNING_JOBS_KEY, job.id)

    try:
        result = await summary_api.process(job)
    except Exception as e:
        log.warning(f"Job {job.id} failed: {e}")

        has_failed = True
        result = str(e)

    updated_job = await update_job(
        expires=redis_exp_seconds if not has_failed else None,
        job_id=job.id,
        end=timeit.default_timer(),
        status=JobStatus.ERROR if has_failed else JobStatus.SUCCESS,
        result=result
    )

    await db.lrem(RUNNING_JOBS_KEY, 0, job.id)

    log.info(f"Job {updated_job.id} duration: {updated_job.computed_duration} seconds")

def create_run_job_task(job: Job) -> asyncio.Task:
    global current_task
    current_task = asyncio.create_task(run_job(job))

async def maybe_run_next_job() -> None:
    if not can_run_next_job():
        return

    await restore_stale_jobs()

    next_job_id = await db.lpop(PENDING_JOBS_KEY)

    if next_job_id:
        log.info(f"Next job id: {next_job_id}")

        next_job = await get_job(next_job_id)
        await run_job(next_job)

async def monitor_candidate_jobs() -> None:
    while True:
        await maybe_run_next_job()
        await asyncio.sleep(TIME_BETWEEN_JOBS_CHECK)

def start_monitoring_jobs() -> asyncio.Task:
    global background_task
    background_task = asyncio.create_task(monitor_candidate_jobs())
