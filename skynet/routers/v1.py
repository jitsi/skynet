from skynet.models.v1.job import Job, JobId
from skynet.modules.ttt.summaries import SummariesChain
from skynet.modules.ttt.jobs import get_job as get_job
from skynet.models.v1.document import DocumentPayload
from skynet.routers.utils import get_router

summary_api = SummariesChain()

router = get_router(1)

@router.post("/action-items")
async def get_action_items(payload: DocumentPayload) -> JobId:
    """
    Starts a job to extract action items from the given payload.
    """

    return await summary_api.start_action_items_job(payload)

@router.post("/summary")
async def get_summary(payload: DocumentPayload) -> JobId:
    """
    Starts a job to summarize the given payload.
    """

    return await summary_api.start_summary_job(payload)

@router.get("/job/{id}")
async def get_job_result(id: str) -> Job | None:
    """
    Returns the job identified by **id**.
    """

    return await get_job(id)
