from fastapi import FastAPI

from skynet.langchain import Langchain
from skynet.models.summary import SummaryPayload

app = FastAPI()
langchain = Langchain()

@app.post("/summary")
def summary(payload: SummaryPayload):
    return langchain.summarize(payload.text)
