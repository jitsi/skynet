import os
import uvicorn

from fastapi import FastAPI
from fastapi.responses import FileResponse

from skynet.apps.openai_api import app as openai_api_app
from skynet.apps.summaries import app as summaries_app

from skynet.logs import get_logger, uvicorn_log_config
from skynet.modules.persistence import init_persistence


log = get_logger('skynet.main')

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

@app.on_event("startup")
async def startup_event():
    log.info('Skynet became self aware')

    await init_persistence()
    log.info('Persistence initialized')


if __name__ == '__main__':
    uvicorn.run('skynet.main:app', port=8000, log_config=uvicorn_log_config)
