import asyncio
import timeit
import uuid

from skynet.models.v1.job import Job, JobStatus, JobType

TIME_BEFORE_DELETION = 60

loop = asyncio.get_running_loop()
jobs = {}
scheduled_for_deletion = []

def create_job(job_type: JobType) -> str:
    id = str(uuid.uuid4())

    jobs[id] = Job(
        id=id,
        type=job_type,
    )

    return id

def get_job(id: str) -> dict:
    job = jobs.get(id)

    if (job and job.status == JobStatus.SUCCESS and id not in scheduled_for_deletion):
        scheduled_for_deletion.append(id)
        loop.call_later(TIME_BEFORE_DELETION, delete_job, id)

    return job

def update_job(id: str, status: JobStatus, result: str) -> None:
    jobs[id].__dict__.update({
        '_end': timeit.default_timer(),
        'status': status,
        'result': result,
    })

    print(f"Job {id} duration: {jobs[id].duration} seconds")

def delete_job(id: str) -> None:
    if id in scheduled_for_deletion:
        scheduled_for_deletion.remove(id)

    del jobs[id]
