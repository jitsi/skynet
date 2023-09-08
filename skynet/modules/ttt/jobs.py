import uuid

from skynet.models.v1.job import Job, JobStatus, JobType

jobs = {}

def create_job(job_type: JobType) -> str:
    id = str(uuid.uuid4())

    jobs[id] = Job(id=id, type=job_type, status=JobStatus.PENDING, result=None, duration=0)

    return id

def get_job(id: str) -> dict:
    return jobs.get(id)

def update_job(id: str, status: JobStatus, result: any, duration: float) -> None:
    jobs[id].__dict__.update({
        'status': status,
        'result': result,
        'duration': duration
    })

def delete_job(id: str) -> None:
    del jobs[id]
