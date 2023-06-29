import os
from fastapi import APIRouter, Depends, FastAPI
from fastapi_versionizer.versionizer import versioned_api_route, versionize

from skynet.auth.bearer import JWTBearer
from skynet.langchain import Langchain
from skynet.models.summary import SummaryPayload

app = FastAPI()
langchain = Langchain()

BYPASS_AUTHORIZATION = os.environ.get('BYPASS_AUTHORIZATION', "False").lower() == 'true'

router = APIRouter(
    dependencies=[Depends(JWTBearer(auto_error=not BYPASS_AUTHORIZATION))],
    responses={
        401: {"description": "Invalid or expired token"},
        403: {"description": "Not enough permissions"}},
    route_class=versioned_api_route(major=1)
)

@router.post("/summarize")
async def summarize(payload: SummaryPayload):
    return await langchain.summarize(payload)

@router.get("/summary/{id}")
async def get_summary(id: str):
    return langchain.get_summary(id)

@router.put("/summary/{id}")
def update_summary(id: str, payload: SummaryPayload):
    return langchain.update_summary(id, payload)

@router.delete("/summary/{id}")
def delete_summary(id: str):
    return langchain.delete_summary(id)

@app.get("/healthz")
def health():
    return {"status": "ok"}

app.include_router(router)

versions = versionize(
    app=app,
    prefix_format='/v{major}',
    docs_url='/docs',
    enable_latest=True,
    sorted_routes=True
)
