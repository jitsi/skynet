from skynet.utils import get_router

from ..jobs import create_job, get_job as get_job
from .models import BaseJob, JobId, JobType, DocumentPayload

router = get_router(1)


@router.post("/action-items")
async def get_action_items(payload: DocumentPayload) -> JobId:
    """
    Starts a job to extract action items from the given payload.
    """

    return await create_job(job_type=JobType.ACTION_ITEMS, payload=payload)


@router.post("/summary")
async def get_summary(payload: DocumentPayload) -> JobId:
    """
    Starts a job to summarize the given payload.
    """

    return await create_job(job_type=JobType.SUMMARY, payload=payload)


@router.get("/job/{id}")
async def get_job_result(id: str) -> BaseJob | None:
    """
    Returns the job identified by **id**.
    """

    job = await get_job(id)

    return BaseJob(**(job.model_dump() | {"duration": job.computed_duration})) if job else None