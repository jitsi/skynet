import subprocess

from skynet import http_client
from skynet.env import (
    llama_n_batch,
    llama_n_ctx,
    llama_n_gpu_layers,
    llama_path,
    openai_api_server_path,
    openai_api_server_port,
)
from skynet.logs import get_logger
from skynet.modules.monitoring import OPENAI_API_RESTART_COUNTER

proc = None

log = get_logger(__name__)


def initialize():
    log.info('Starting OpenAI API server...')

    global proc

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
    # https://github.com/ggerganov/llama.cpp/blob/master/examples/server/README.md#get-health-returns-heath-check-result
    try:
        response = await http_client.get(f'http://localhost:{openai_api_server_port}/health')

        if response.get('error'):
            return False

        return response.get('status') == 'ok'
    except Exception:
        return False


def destroy():
    log.info('Killing OpenAI API subprocess...')

    proc.kill()


def restart():
    log.info('Restarting OpenAI API server...')

    OPENAI_API_RESTART_COUNTER.inc()

    destroy()
    initialize()


__all__ = ['destroy', 'initialize', 'restart']
