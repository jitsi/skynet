from fastapi import Depends, HTTPException, Request
from fastapi_versionizer.versionizer import api_version

from skynet.env import live_summary_minimum_payload_length, summary_minimum_payload_length

from skynet.utils import get_app_id, get_customer_id, get_router

from ..jobs import create_job, get_job as get_job
from .models import (
    ActionItemsDocumentPayload,
    BaseJob,
    DocumentMetadata,
    DocumentPayload,
    JobId,
    JobType,
    ProcessTextDocumentPayload,
    SummaryDocumentPayload,
    TableOfContentsDocumentPayload,
)

router = get_router()


def get_metadata(request: Request) -> DocumentMetadata:
    return DocumentMetadata(app_id=get_app_id(request), customer_id=get_customer_id(request))


def validate_summaries_payload(payload: DocumentPayload) -> None:
    min_length = live_summary_minimum_payload_length if payload.is_live_summary else summary_minimum_payload_length
    if len(payload.text.strip()) < min_length:
        raise HTTPException(status_code=422, detail="Payload is too short")


def validate_process_text_payload(payload: DocumentPayload) -> None:
    if not payload.prompt.strip():
        raise HTTPException(status_code=422, detail="Prompt is required")


@api_version(1)
@router.post("/action-items", dependencies=[Depends(validate_summaries_payload)])
async def action_items(payload: ActionItemsDocumentPayload, request: Request) -> JobId:
    """
    Starts a job to extract action items from the given payload.
    """

    return await create_job(job_type=JobType.ACTION_ITEMS, payload=payload, metadata=get_metadata(request))


@api_version(1)
@router.post("/table-of-contents", dependencies=[Depends(validate_summaries_payload)])
async def table_of_contents(payload: TableOfContentsDocumentPayload, request: Request) -> JobId:
    """
    Starts a job to extract action items from the given payload.
    """

    return await create_job(job_type=JobType.TABLE_OF_CONTENTS, payload=payload, metadata=get_metadata(request))


@api_version(1)
@router.post("/summary", dependencies=[Depends(validate_summaries_payload)])
async def summary(payload: SummaryDocumentPayload, request: Request) -> JobId:
    """
    Starts a job to summarize the given payload.
    """

    return await create_job(job_type=JobType.SUMMARY, payload=payload, metadata=get_metadata(request))


@api_version(1)
@router.post("/process-text", dependencies=[Depends(validate_process_text_payload)])
async def process_text(payload: ProcessTextDocumentPayload, request: Request) -> JobId:
    """
    Starts a job to process the given text.
    """

    return await create_job(job_type=JobType.PROCESS_TEXT, payload=payload, metadata=get_metadata(request))


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
