import os
import sys
import uvicorn

from fastapi import FastAPI
from fastapi.responses import FileResponse

from skynet.env import enabled_apps
from skynet.logs import get_logger, uvicorn_log_config

log = get_logger('skynet.main')

supported_apps = {'openai-api', 'summaries'}
enable_apps = supported_apps.intersection(enabled_apps)

if not enabled_apps:
    log.warn('No apps enabled!')
    sys.exit(1)

log.info(f'Enabled apps: {enable_apps}')

app = FastAPI()

if 'openai-api' in enable_apps:
    from skynet.apps.openai_api import app as openai_api_app

    app.mount("/openai-api", openai_api_app)

if 'summaries' in enable_apps:
    from skynet.apps.summaries import app as summaries_app

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

    if 'summaries' in enable_apps:
        from skynet.apps.summaries import app_startup as summariees_startup

        await summariees_startup()


if __name__ == '__main__':
    uvicorn.run('skynet.main:app', port=8000, log_config=uvicorn_log_config)
