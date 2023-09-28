import asyncio
import timeit
import uuid

from skynet.models.v1.job import Job, JobStatus, JobType
from skynet.modules.persistence import db

TIME_BEFORE_DELETION = 60

loop = asyncio.get_running_loop()
scheduled_for_deletion = []

def create_job(job_type: JobType) -> str:
    id = str(uuid.uuid4())

    job = Job(
        end=timeit.default_timer(),
        id=id,
        start=timeit.default_timer(),
        type=job_type,
    )

    db.set(id, Job.model_dump_json(job))

    return id

def get_job(id: str) -> dict:
    json = db.get(id)
    job = Job.model_validate_json(json) if json else None

    if (job and job.status == JobStatus.SUCCESS and id not in scheduled_for_deletion):
        scheduled_for_deletion.append(id)
        loop.call_later(TIME_BEFORE_DELETION, delete_job, id)

    return job

def update_job(id: str, status: JobStatus, result: str) -> None:
    json = db.get(id)

    if not json:
        return

    job = Job.model_validate_json(db.get(id))
    job.__setattr__('status', status)
    job.__setattr__('result', result)
    job.__setattr__('end', timeit.default_timer())

    db.set(id, Job.model_dump_json(job))

    print(f"Job {id} duration: {job.duration} seconds")

def delete_job(id: str) -> None:
    if id in scheduled_for_deletion:
        scheduled_for_deletion.remove(id)

    db.delete(id)
