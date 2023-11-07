import asyncio
import os
import sys

from fastapi import FastAPI
from fastapi.responses import FileResponse

from skynet.env import enable_metrics, modules
from skynet.logs import get_logger

from skynet.utils import create_webserver

log = get_logger(__name__)

if not modules:
    log.warn('No modules enabled!')
    sys.exit(1)

log.info(f'Enabled modules: {modules}')

app = FastAPI()

if 'openai-api' in modules:
    from skynet.modules.ttt.openai_api.app import app as openai_api_app

    app.mount('/openai-api', openai_api_app)

if 'summaries:dispatcher' in modules:
    from skynet.modules.ttt.summaries.app import app as summaries_app

    app.mount('/summaries', summaries_app)


@app.get('/')
def root():
    return FileResponse(os.path.join(os.path.dirname(__file__), 'index.html'))


@app.on_event('startup')
async def startup_event():
    log.info('Skynet became self aware')

    if 'summaries:dispatcher' in modules:
        from skynet.modules.ttt.summaries.app import app_startup as summaries_startup

        await summaries_startup()

    if 'summaries:executor' in modules:
        from skynet.modules.ttt.summaries.app import executor_startup as executor_startup

        await executor_startup()


async def main():
    tasks = [asyncio.create_task(create_webserver('skynet.main:app', port=8000))]

    if enable_metrics:
        tasks.insert(0, asyncio.create_task(create_webserver('skynet.metrics:metrics', port=8001)))

    await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(e)
        sys.exit(0)
