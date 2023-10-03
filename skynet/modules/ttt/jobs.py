import asyncio
import time
import timeit
import uuid
from skynet.logs import get_logger

from skynet.models.v1.document import DocumentPayload
from skynet.models.v1.job import Job, JobId, JobStatus, JobType
from skynet.modules.persistence import db
from skynet.modules.ttt.summaries import SummariesChain

log = get_logger('skynet.jobs')

summary_api = SummariesChain()

TIME_BEFORE_DELETION = 60 * 10 # 10 minutes
TIME_BETWEEN_JOBS_CHECK = 10
PENDING_JOBS_KEY = "jobs:pending"
RUNNING_JOBS_KEY = "jobs:running"

is_job_running = False
background_tasks = set()

def can_run_next_job() -> bool:
    return not is_job_running

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
        log.info(f"Restoring {len(stale_jobs)} stale job(s)")
        await db.rpush(PENDING_JOBS_KEY, *[job.id for job in stale_jobs])

async def create_job(job_type: JobType, payload: DocumentPayload) -> JobId:
    """Create a job and add it to the db queue if it can't be started immediately."""

    id = str(uuid.uuid4())

    job = Job(
        id=id,
        payload=payload,
        # debatable if this should be here or when job starts
        start=timeit.default_timer(),
        type=job_type
    )

    await db.set(id, Job.model_dump_json(job))

    if can_run_next_job():
        global is_job_running
        is_job_running = True

        create_run_job_task(job)
    else:
        await db.rpush(PENDING_JOBS_KEY, id)

    return JobId(id=id)

async def get_job(id: str) -> Job:
    job_json = await db.get(id)
    job = Job.model_validate_json(job_json) if job_json else None

    return job

async def update_job(id: str, expires_at: int = None, **kwargs) -> Job:
    """Update a job in the db."""
    job_json = await db.get(id)

    # deserialize and merge
    job = Job(**(Job.model_validate_json(job_json).model_dump() | kwargs))

    # serialize changes and save to db
    await db.set(id, Job.model_dump_json(job), exat=expires_at)

    return job

async def run_job(job: Job) -> None:
    has_failed = False
    result = None
    worker_id = await db.db.client_id()

    await update_job(
        id=job.id,
        status=JobStatus.RUNNING,
        worker_id=worker_id)

    await db.rpush(RUNNING_JOBS_KEY, job.id)

    try:
        result = await summary_api.process(job)
    except Exception as e:
        has_failed = True
        result = str(e)

    updated_job = await update_job(
        expires_at=int(time.time()) + TIME_BEFORE_DELETION if not has_failed else None,
        id=job.id,
        end=timeit.default_timer(),
        status=JobStatus.ERROR if has_failed else JobStatus.SUCCESS,
        result=result
    )

    await db.lrem(RUNNING_JOBS_KEY, 0, job.id)

    global is_job_running
    is_job_running = False

    log.info(f"Job {updated_job.id} duration: {updated_job.computed_duration} seconds")

def create_run_job_task(job: Job) -> asyncio.Task:
    task = asyncio.create_task(run_job(job))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

async def maybe_run_next_job() -> None:
    if not can_run_next_job():
        return

    next_job_id = await db.lpop(PENDING_JOBS_KEY)

    if next_job_id:
        log.info(f"Next job id: {next_job_id}")

        next_job = await get_job(next_job_id)
        await run_job(next_job)
    else:
        await restore_stale_jobs()

async def monitor_candidate_jobs() -> None:
    while True:
        await maybe_run_next_job()
        await asyncio.sleep(TIME_BETWEEN_JOBS_CHECK)

def start_monitoring_jobs() -> asyncio.Task:
    task = asyncio.create_task(monitor_candidate_jobs())
    background_tasks.add(task)
