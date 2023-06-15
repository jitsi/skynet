from fastapi import FastAPI
from fastapi_versionizer.versionizer import api_version, versionize

from skynet.langchain import Langchain
from skynet.models.summary import SummaryPayload

app = FastAPI()
langchain = Langchain()

@api_version(1)
@app.post("/summarize")
async def summarize(payload: SummaryPayload):
    return await langchain.summarize(payload)

@app.get("/summary/{id}")
async def get_summary(id: str):
    return langchain.get_summary(id)

@app.put("/summary/{id}")
def update_summary(id: str, payload: SummaryPayload):
    return langchain.update_summary(id, payload)

@app.delete("/summary/{id}")
def delete_summary(id: str):
    return langchain.delete_summary(id)

versions = versionize(
    app=app,
    prefix_format='/v{major}',
    docs_url='/docs',
    enable_latest=True,
    latest_prefix='/latest',
    sorted_routes=True
)
