import asyncio

from fastapi import FastAPI

from skynet import http_client
from skynet.env import app_port, llama_n_ctx, llama_path, openai_api_base_url, use_vllm
from skynet.logs import get_logger
from skynet.utils import dependencies, responses

log = get_logger(__name__)


async def run_vllm_server(args, app: FastAPI):
    from vllm.entrypoints.openai.api_server import build_async_engine_client, init_app_state, router

    async with build_async_engine_client(args) as engine_client:
        app.include_router(router, dependencies=dependencies, responses=responses)

        model_config = await engine_client.get_model_config()
        init_app_state(engine_client, model_config, app.state, args)


def initialize(app: FastAPI | None = None):
    log.info('Starting OpenAI API server...')

    if use_vllm:
        from vllm.entrypoints.openai.cli_args import make_arg_parser
        from vllm.utils import FlexibleArgumentParser

        parser = FlexibleArgumentParser(description="vLLM OpenAI-Compatible RESTful API server.")
        parser = make_arg_parser(parser)
        args = parser.parse_args(
            [
                '--disable-frontend-multiprocessing',  # disable running the engine in a separate process
                '--disable-log-requests',
                '--model',
                llama_path,
                '--gpu_memory_utilization',
                '0.99',
                '--max-model-len',
                str(llama_n_ctx),
                '--port',
                str(app_port),
            ]
        )

        asyncio.create_task(run_vllm_server(args, app))


async def is_ready():
    url = f'{openai_api_base_url}/health' if use_vllm else openai_api_base_url

    try:
        response = await http_client.get(url, 'text')

        if use_vllm:
            return response == ''
        else:
            return response == 'Ollama is running'
    except Exception as e:
        log.warning('Error checking if the server is ready: ', e)
        return False


__all__ = ['initialize', 'is_ready']
