import os
import sys
import uvicorn

from fastapi import FastAPI
from fastapi.responses import FileResponse

from skynet.env import enabled_modules
from skynet.logs import get_logger, uvicorn_log_config

log = get_logger('skynet.main')

supported_modules = {'openai-api', 'summaries'}
modules = supported_modules.intersection(enabled_modules)

if not modules:
    log.warn('No modules enabled!')
    sys.exit(1)

log.info(f'Enabled modules: {modules}')

app = FastAPI()

if 'openai-api' in modules:
    from skynet.modules.ttt.openai_api.app import app as openai_api_app

    app.mount("/openai-api", openai_api_app)

if 'summaries' in modules:
    from skynet.modules.ttt.summaries.app import app as summaries_app

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

    if 'summaries' in modules:
        from skynet.modules.ttt.summaries.app import app_startup as summariees_startup

        await summariees_startup()


if __name__ == '__main__':
    uvicorn.run('skynet.main:app', port=8000, log_config=uvicorn_log_config)
