import random

from fastapi import FastAPI, Request
from fastapi_versionizer.versionizer import Versionizer

from skynet import http_client
from skynet.auth.openai import setup_credentials
from skynet.env import echo_requests_base_url, echo_requests_percent, echo_requests_token
from skynet.logs import get_logger
from skynet.modules.ttt.openai_api.app import initialize as initialize_openai_api
from skynet.utils import create_app

from .jobs import start_monitoring_jobs
from .persistence import db
from .processor import initialize as initialize_summaries
from .v1.router import router as v1_router


log = get_logger(__name__)

app = create_app()
app.include_router(v1_router)

if echo_requests_base_url:
    log.info(f'Echoing requests enabled for url: {echo_requests_base_url}')

    @app.middleware("http")
    async def echo_requests(request: Request, call_next):
        if request.method == 'POST':
            counter = random.randrange(1, 101)

            if counter <= echo_requests_percent:
                try:
                    await http_client.post(
                        f'{echo_requests_base_url}{request.url.path}',
                        headers={'Authorization': f'Bearer {echo_requests_token}'},
                        json=await request.json(),
                    )
                except Exception as e:
                    log.warning(f'Failed to echo request: {e}')

        return await call_next(request)


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
    await db.close()
    log.info('Persistence shutdown')


__all__ = ['app', 'executor_startup', 'executor_shutdown', 'app_startup']
