from fastapi import HTTPException, Request
from fastapi_versionizer.versionizer import api_version

from skynet.utils import get_router

from ..jobs import create_job, get_job as get_job
from .models import BaseJob, DocumentMetadata, DocumentPayload, JobId, JobType

router = get_router()


def get_customer_id(request: Request) -> str:
    id = request.query_params.get("customerId")

    if not id:
        id = request.state.decoded_jwt.get("cid") if hasattr(request.state, 'decoded_jwt') else None

    return id


def get_app_id(request: Request) -> str:
    return request.state.decoded_jwt.get('appId') if hasattr(request.state, 'decoded_jwt') else None


def get_metadata(request: Request) -> DocumentMetadata:
    return DocumentMetadata(app_id=get_app_id(request), customer_id=get_customer_id(request))


@api_version(1)
@router.post("/action-items")
async def get_action_items(payload: DocumentPayload, request: Request) -> JobId:
    """
    Starts a job to extract action items from the given payload.
    """

    return await create_job(job_type=JobType.ACTION_ITEMS, payload=payload, metadata=get_metadata(request))


@api_version(1)
@router.post("/summary")
async def get_summary(payload: DocumentPayload, request: Request) -> JobId:
    """
    Starts a job to summarize the given payload.
    """

    return await create_job(job_type=JobType.SUMMARY, payload=payload, metadata=get_metadata(request))


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
