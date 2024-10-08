import os
import subprocess

from skynet import http_client
from skynet.env import (
    llama_cpp_server_path,
    llama_n_batch,
    llama_n_ctx,
    llama_n_gpu_layers,
    llama_path,
    openai_api_base_url,
    openai_api_server_port,
    vllm_server_path,
)
from skynet.logs import get_logger
from skynet.modules.monitoring import OPENAI_API_RESTART_COUNTER
from skynet.utils import get_device

proc = None
use_vllm = get_device() == 'cuda'

log = get_logger(__name__)


def initialize():
    log.info('Starting OpenAI API server...')

    global proc

    if use_vllm:
        openai_api_server_path = vllm_server_path
        proc = subprocess.Popen(
            f'python -m {openai_api_server_path} \
                --model {llama_path} \
                --gpu_memory_utilization 0.95 \
                --max-model-len {llama_n_ctx} \
                --port {openai_api_server_port}'.split(),
            shell=False,
        )
    else:
        openai_api_server_path = llama_cpp_server_path
        proc = subprocess.Popen(
            f'{openai_api_server_path} \
                --batch-size {llama_n_batch} \
                --ctx-size {llama_n_ctx} \
                --flash-attn \
                --model {llama_path} \
                --n-gpu-layers {llama_n_gpu_layers} \
                --port {openai_api_server_port}'.split(),
            shell=False,
        )

    if proc.poll() is not None:
        log.error(f'Failed to start OpenAI API server from {openai_api_server_path}')
    else:
        log.info(f'OpenAI API server started from {openai_api_server_path}')


async def is_ready():
    try:
        await http_client.get(f'{openai_api_base_url}/health', 'text' if use_vllm else 'json')

        return True
    except Exception:
        return False


def destroy():
    log.info('Killing OpenAI API subprocess...')

    proc.kill()


def restart():
    log.info('Restarting Skynet...')

    OPENAI_API_RESTART_COUNTER.inc()

    # rely on the supervisor to restart the process
    os._exit(1)


__all__ = ['destroy', 'initialize', 'restart']
