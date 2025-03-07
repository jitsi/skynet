from fastapi import Depends, HTTPException, Request
from fastapi_versionizer.versionizer import api_version

from skynet.auth.customer_id import CustomerId
from skynet.logs import get_logger
from skynet.modules.ttt.assistant.v1.models import AssistantDocumentPayload, AssistantResponse, RagConfig, RagPayload
from skynet.modules.ttt.processor import process
from skynet.modules.ttt.rag.app import get_vector_store
from skynet.modules.ttt.summaries.v1.models import DocumentMetadata, Job, JobType
from skynet.utils import get_customer_id, get_router

router = get_router()
log = get_logger(__name__)


@api_version(1)
@router.get('/rag')
async def get_rag_db(customer_id=Depends(CustomerId())) -> RagConfig:
    """
    Check if a RAG database exists.
    """

    store = await get_vector_store()
    config = await store.get_config(customer_id)

    if config:
        return config

    raise HTTPException(status_code=404, detail='RAG database not found')


@api_version(1)
@router.post('/rag')
async def create_rag_db(payload: RagPayload, customer_id=Depends(CustomerId())) -> RagConfig:
    """
    Create / update a RAG database.
    """

    store = await get_vector_store()
    return await store.update_from_urls(payload, customer_id)


@api_version(1)
@router.delete('/rag')
async def delete_rag_db(customer_id=Depends(CustomerId())) -> None:
    """
    Delete a RAG database.
    """

    store = await get_vector_store()
    config = await store.get_config(customer_id)

    if not config:
        raise HTTPException(status_code=404, detail='RAG database not found')

    await store.delete(customer_id)


@api_version(1)
@router.post('/assist')
async def assist(payload: AssistantDocumentPayload, request: Request) -> AssistantResponse:
    """
    Assist the user using a RAG database.
    """

    job = Job(
        payload=payload,
        type=JobType.ASSIST,
        metadata=DocumentMetadata(customer_id=get_customer_id(request)),
    )

    response = await process(job)

    return AssistantResponse(text=response)
