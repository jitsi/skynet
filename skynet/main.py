import logging
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse

from skynet.apps.openai_api import app as openai_api_app
from skynet.apps.summaries import app as summaries_app

from skynet.env import AccessLogSuppressor

logging.getLogger('uvicorn.access').addFilter(AccessLogSuppressor())


app = FastAPI()
app.mount("/openai-api", openai_api_app)
app.mount("/summaries", summaries_app)

@app.get("/")
def root():
    return FileResponse(os.path.join(os.path.dirname(__file__), 'index.html'))

@app.get("/healthz")
def health():
    """
    Health checking for k8s.
    """

    return {"status": "ok"}
