import asyncio
import timeit
import uuid

from skynet.models.v1.job import Job, JobStatus, JobType
from skynet.modules.persistence import db

loop = asyncio.get_running_loop()


async def create_job(job_type: JobType) -> str:
    job_id = str(uuid.uuid4())

    job = Job(
        end=timeit.default_timer(),
        id=job_id,
        start=timeit.default_timer(),
        type=job_type,
    )

    await db.set(job_id, Job.model_dump_json(job))

    return job_id


async def get_job(job_id: str) -> dict:
    json = await db.get(job_id)
    job = Job.model_validate_json(json) if json is not None else None
    return job


async def update_job(job_id: str, status: JobStatus, result: str) -> None:
    json = await db.get(job_id)

    if json is None:
        return

    job = Job.model_validate_json(json)
    job.__setattr__('status', status)
    job.__setattr__('result', result)
    job.__setattr__('end', timeit.default_timer())

    await db.set(job_id, Job.model_dump_json(job))

    print(f'Job {job_id} duration: {job.duration} seconds')

