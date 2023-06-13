from fastapi import FastAPI

from skynet.langchain import Langchain
from skynet.models.summary import SummaryPayload

app = FastAPI()
langchain = Langchain()
version = "v1"

@app.post(f"/{version}/summary")
def create_summary(payload: SummaryPayload):
    return langchain.summarize(payload.text)

@app.get(f"/{version}/summary/" + "{id}")
def get_summary(id: str):
    return langchain.get_summary(id)

@app.put(f"/{version}/summary/" + "{id}")
def update_summary(id: str, payload: SummaryPayload):
    return langchain.update_summary(id, payload.text)

@app.delete(f"/{version}/summary/" + "{id}")
def delete_summary(id: str):
    return langchain.delete_summary(id)
