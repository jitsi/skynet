from fastapi_versionizer.versionizer import Versionizer

from skynet.auth.openai import setup_credentials
from skynet.logs import get_logger
from skynet.modules.ttt.openai_api.app import destroy as destroy_openai_api, initialize as initialize_openai_api
from skynet.utils import create_app

from .jobs import start_monitoring_jobs
from .persistence import db
from .processor import initialize as initialize_summaries
from .v1.router import router as v1_router


log = get_logger(__name__)

app = create_app()
app.include_router(v1_router)

Versionizer(app=app, prefix_format='/v{major}', sort_routes=True).versionize()


async def app_startup():
    log.info('summaries:dispatcher module initialized')

    await db.initialize()
    log.info('Persistence initialized')


async def executor_startup():
    await setup_credentials()

    initialize_openai_api()

    initialize_summaries()
    log.info('summaries:executor module initialized')

    await db.initialize()
    log.info('Persistence initialized')

    start_monitoring_jobs()
    log.info('Jobs monitoring started')


async def executor_shutdown():
    destroy_openai_api()

    await db.close()
    log.info('Persistence shutdown')


__all__ = ['app', 'executor_startup', 'executor_shutdown', 'app_startup']
