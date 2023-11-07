from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi_versionizer.versionizer import versionize

from skynet.logs import get_logger

from .persistence import db
from .jobs import start_monitoring_jobs
from .processor import initialize as initialize_summaries
from .v1.router import router as v1_router


log = get_logger(__name__)

app = FastAPI()
app.include_router(v1_router)

versionize(app=app, prefix_format='/v{major}', docs_url='/docs', enable_latest=False, sorted_routes=True)


@app.get("/")
def root():
    return RedirectResponse(url='v1/docs')


async def app_startup():
    log.info('summaries:dispatcher module initialized')

    await db.initialize()
    log.info('Persistence initialized')


async def executor_startup():
    initialize_summaries()
    log.info('summaries:executor module initialized')

    await db.initialize()
    log.info('Persistence initialized')

    start_monitoring_jobs()


__all__ = ['app', 'executor_startup', 'app_startup']
