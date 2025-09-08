import asyncio
import importlib.metadata
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse

from skynet import http_client
from skynet.env import app_port, device, enable_haproxy_agent, enable_metrics, is_mac, modules
from skynet.haproxy_agent import create_tcpserver
from skynet.logs import get_logger
from skynet.utils import create_app, create_webserver

log = get_logger(__name__)

if not modules:
    log.warning('No modules enabled!')
    sys.exit(1)

log.info(f'Enabled modules: {modules}')

if device == 'cuda':
    log.info('Using Nvidia GPU')
elif is_mac:
    log.info('Using Apple GPU')
else:
    log.info('Using CPU')


@asynccontextmanager
async def lifespan(main_app: FastAPI):
    log.info(f'Skynet {importlib.metadata.version("skynet")} became self aware')

    if 'streaming_whisper' in modules:
        from skynet.modules.stt.streaming_whisper.app import app as streaming_whisper_app
        from skynet.modules.stt.vox.app import app as vox_app

        main_app.mount('/streaming-whisper', streaming_whisper_app)
        main_app.mount('/vox', vox_app)

    if 'assistant' in modules:
        from skynet.modules.ttt.assistant.app import app as rag_app, app_startup as assistant_startup

        main_app.mount('/assistant', rag_app)
        await assistant_startup()

    if 'customerconfigs' in modules:
        from skynet.modules.ttt.customerconfigs.app import app as customerconfigs_app, app_startup as customerconfigs_startup

        main_app.mount('/customerconfigs', customerconfigs_app)
        await customerconfigs_startup()

    if 'summaries:dispatcher' in modules:
        from skynet.modules.ttt.openai_api.app import app as openai_api_app
        from skynet.modules.ttt.summaries.app import app as summaries_app, app_startup as summaries_startup

        main_app.mount('/summaries', summaries_app)
        main_app.mount('/openai', openai_api_app)

        await summaries_startup()

    if 'summaries:executor' in modules:
        from skynet.modules.ttt.summaries.app import executor_startup as executor_startup

        await executor_startup()

    yield

    log.info('Skynet is shutting down')

    if 'summaries:executor' in modules:
        from skynet.modules.ttt.summaries.app import executor_shutdown as executor_shutdown

        await executor_shutdown()

    if 'assistant' in modules:
        from skynet.modules.ttt.assistant.app import app_shutdown as assistant_shutdown

        await assistant_shutdown()

    if 'customerconfigs' in modules:
        from skynet.modules.ttt.customerconfigs.app import app_shutdown as customerconfigs_shutdown

        await customerconfigs_shutdown()

    await http_client.close()


app = create_app(lifespan=lifespan)


@app.get('/')
def root():
    return FileResponse(os.path.join(os.path.dirname(__file__), 'index.html'))


async def main():
    tasks = [asyncio.create_task(create_webserver('skynet.main:app', port=app_port))]

    if enable_metrics:
        tasks.append(asyncio.create_task(create_webserver('skynet.metrics:metrics', port=8001)))

    if enable_haproxy_agent and 'streaming_whisper' in modules:
        # haproxy agent check tcp server
        tasks.append(asyncio.create_task(create_tcpserver(port=8002)))
        # sidecar rest endpoint for the autoscaler
        tasks.append(asyncio.create_task(create_webserver('skynet.haproxy_agent:autoscaler_rest_app', port=8003)))

    await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(e)
        sys.exit(0)
    except KeyboardInterrupt:
        pass
