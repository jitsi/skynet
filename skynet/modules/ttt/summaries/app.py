from fastapi import FastAPI
from fastapi_versionizer.versionizer import Versionizer

from skynet.logs import get_logger

from .jobs import start_monitoring_jobs
from .persistence import db
from .processor import initialize as initialize_summaries
from .v1.router import router as v1_router


log = get_logger(__name__)

app = FastAPI()
app.include_router(v1_router)

Versionizer(app=app, prefix_format='/v{major}', sort_routes=True).versionize()


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
