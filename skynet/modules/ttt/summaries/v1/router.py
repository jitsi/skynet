from fastapi import Header, HTTPException, Request
from fastapi_versionizer.versionizer import api_version

from skynet.auth.bearer import JWTBearer
from skynet.auth.jwt import authorize

from skynet.utils import get_router

from ..jobs import create_job, get_job as get_job
from .models import BaseJob, DocumentPayload, JobId, JobType

router = get_router()


@api_version(1)
@router.post("/action-items")
async def get_action_items(payload: DocumentPayload) -> JobId:
    """
    Starts a job to extract action items from the given payload.
    """

    return create_job(job_type=JobType.ACTION_ITEMS, payload=payload)


@api_version(1)
@router.post("/summary")
async def get_summary(payload: DocumentPayload, request: Request) -> JobId:
    """
    Starts a job to summarize the given payload.
    """

    bearer_jwt: JWTBearer = await JWTBearer().__call__(request)
    decoded_jwt = await authorize(bearer_jwt)
    customer_id = decoded_jwt.get("cid")

    return create_job(job_type=JobType.SUMMARY, payload=payload, customer_id=customer_id)


@api_version(1)
@router.get("/job/{id}")
async def get_job_result(id: str) -> BaseJob | None:
    """
    Returns the job identified by **id**.
    """

    job = await get_job(id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return BaseJob(**(job.model_dump() | {"duration": job.computed_duration}))
