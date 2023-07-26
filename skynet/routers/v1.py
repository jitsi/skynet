from skynet.modules.ttt.summaries import SummariesChain
from skynet.models.v1.summary import SummaryPayload, SummaryResult
from skynet.routers.utils import get_router

summary_api = SummariesChain()

router = get_router(1)

@router.post("/summarize")
async def summarize(payload: SummaryPayload) -> SummaryResult:
    """
    Summarizes the given payload. It's not stored in memory.
    """

    return await summary_api.summarize(payload)

@router.get("/summary/{id}")
async def get_summary(id: str) -> SummaryResult:
    """
    Summarizes based on the summary context for the given **id**.
    """

    return await summary_api.get_summary(id)

@router.put("/summary/{id}")
def update_summary_context(id: str, payload: SummaryPayload):
    """
    Updates a summary context identified by **id** with the given payload (or creates a new one if it doesn't exist).
    """

    return summary_api.update_summary_context(id, payload)

@router.delete("/summary/{id}")
def delete_summary_context(id: str) -> bool:
    """
    Deletes an in-memory summary context identified by **id**.
    """

    return summary_api.delete_summary_context(id)
