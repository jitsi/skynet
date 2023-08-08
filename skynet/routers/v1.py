from skynet.models.v1.action_items import ActionItemsResult
from skynet.modules.ttt.summaries import SummariesChain
from skynet.models.v1.summary import SummaryResult
from skynet.models.v1.document import DocumentPayload
from skynet.routers.utils import get_router

summary_api = SummariesChain()

router = get_router(1)

@router.post("/summary")
async def get_summary(payload: DocumentPayload) -> SummaryResult:
    """
    Summarizes the given payload. It's not stored in memory.
    """

    return await summary_api.get_summary_from_text(payload)

@router.post("/action-items")
async def get_action_items_from_text(payload: DocumentPayload) -> ActionItemsResult:
    """
    Extracts action items from the given payload. It's not stored in memory.
    """

    return await summary_api.get_action_items_from_text(payload)

@router.get("/action-items/{id}")
async def get_action_items(id: str) -> ActionItemsResult:
    """
    Extracts action items based on the document context for the given **id**.
    """

    return await summary_api.get_action_items_from_id(id)

@router.get("/summary/{id}")
async def get_summary(id: str) -> SummaryResult:
    """
    Summarizes based on the document context for the given **id**.
    """

    return await summary_api.get_summary_from_id(id)

@router.put("/document/{id}")
def update_document_context(id: str, payload: DocumentPayload):
    """
    Updates a document context identified by **id** with the given payload (or creates a new one if it doesn't exist).
    """

    return summary_api.update_document_context(id, payload)

@router.delete("/document/{id}")
def delete_document_context(id: str) -> bool:
    """
    Deletes an in-memory document context identified by **id**.
    """

    return summary_api.delete_document_context(id)
