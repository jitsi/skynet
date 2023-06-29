from skynet.langchain import Langchain
from skynet.models.v1.summary import SummaryPayload
from skynet.routers.utils import get_router

langchain = Langchain()

router = get_router(1)

@router.post("/summarize")
async def summarize(payload: SummaryPayload):
    """
    Summarizes the given payload. It's not stored in memory.
    """

    return await langchain.summarize(payload)

@router.get("/summary/{id}")
async def get_summary(id: str):
    """
    Returns the current summary for the given **id**.
    """

    return langchain.get_summary(id)

@router.put("/summary/{id}")
def update_summary(id: str, payload: SummaryPayload):
    """
    Updates an existing summary identified by **id** with the given payload.
    """

    return langchain.update_summary(id, payload)

@router.delete("/summary/{id}")
def delete_summary(id: str):
    """
    Deletes an in-memory summary identified by **id**.
    """

    return langchain.delete_summary(id)
