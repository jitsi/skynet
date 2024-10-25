import asyncio
import subprocess

from fastapi import FastAPI

from skynet import http_client
from skynet.env import (
    llama_cpp_server_path,
    llama_n_batch,
    llama_n_ctx,
    llama_n_gpu_layers,
    llama_path,
    openai_api_base_url,
    openai_api_server_port,
    use_vllm,
)
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
                str(openai_api_server_port),
            ]
        )

        asyncio.create_task(run_vllm_server(args, app))
    else:
        subprocess.Popen(
            f'{llama_cpp_server_path} \
                --batch-size {llama_n_batch} \
                --ctx-size {llama_n_ctx} \
                --flash-attn \
                --model {llama_path} \
                --n-gpu-layers {llama_n_gpu_layers} \
                --port {openai_api_server_port}'.split(),
            shell=False,
        )


async def is_ready():
    try:
        response = await http_client.get(f'{openai_api_base_url}/health', 'text' if use_vllm else 'json')

        if use_vllm:
            return response == ''

        return True
    except Exception:
        return False


__all__ = ['initialize', 'is_ready']
