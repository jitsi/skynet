import subprocess
import time

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
                --uvicorn-log-level debug \
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
        log.info(f'OpenAI API server started from {openai_api_server_path}, with PID {proc.pid}')


async def is_ready():
    try:
        await http_client.get(f'{openai_api_base_url}/health', 'text' if use_vllm else 'json')

        return True
    except Exception:
        return False


def destroy():
    log.info('Killing OpenAI API subprocess...')

    if use_vllm:
        subprocess.run(f'nvidia-smi --query-compute-apps=pid --format=csv,noheader | xargs -n1 kill -9', shell=True)

    # subprocess.run(f'lsof -t -i tcp:{openai_api_server_port} | xargs -n1 kill -9', shell=True)

    proc.kill()
    time.sleep(5)


def restart():
    log.info('Restarting OpenAI API server...')

    OPENAI_API_RESTART_COUNTER.inc()

    destroy()
    initialize()


__all__ = ['destroy', 'initialize', 'restart']
