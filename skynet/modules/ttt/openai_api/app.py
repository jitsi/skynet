import subprocess

from skynet.env import (
    llama_n_batch,
    llama_n_ctx,
    llama_n_gpu_layers,
    llama_path,
    openai_api_server_dir,
    openai_api_server_port,
)
from skynet.logs import get_logger

proc = None
log = get_logger(__name__)


def initialize():
    global proc
    proc = subprocess.Popen(
        f'{openai_api_server_dir} \
            -m {llama_path} \
            -b {llama_n_batch} \
            -c {llama_n_ctx} \
            -ngl {llama_n_gpu_layers} \
            --port {openai_api_server_port}'.split(),
        shell=False,
    )

    if proc.poll() is not None:
        log.error(f'Failed to start OpenAI API server from {openai_api_server_dir}')
    else:
        log.info(f'OpenAI API server started from {openai_api_server_dir}')


def destroy():
    proc.kill()
    log.info('OpenAI API subprocess destroyed')


__all__ = ['destroy', 'initialize']
