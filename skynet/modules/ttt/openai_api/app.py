import subprocess
import sys

from skynet import http_client
from skynet.env import llama_n_ctx, llama_path, openai_api_base_url, openai_api_port, use_oci, use_vllm, disable_llm_health_check
from skynet.logs import get_logger
from skynet.modules.ttt.openai_api.slim_router import router as slim_router
from skynet.utils import create_app

log = get_logger(__name__)

app = create_app()
app.include_router(slim_router)


def initialize():
    if not use_vllm:
        return

    log.info(f'Starting vLLM server on port {openai_api_port} using model {llama_path}')

    proc = subprocess.Popen(
        [
            sys.executable,
            '-m',
            'vllm.entrypoints.openai.api_server',
            '--disable-log-requests',
            '--model',
            llama_path,
            '--gpu_memory_utilization',
            str(0.90),
            '--max-model-len',
            str(llama_n_ctx),
            '--port',
            str(openai_api_port),
        ],
        shell=False,
    )

    if proc.poll() is not None:
        log.error('Failed to start vLLM OpenAI API server')
    else:
        log.info('vLLM OpenAI API server started')


async def is_ready():
    if use_oci or disable_llm_health_check:
        return True

    url = f'{openai_api_base_url}/health' if use_vllm else openai_api_base_url

    try:
        response = await http_client.get(url, 'text')

        if use_vllm:
            return response == ''
        else:
            return response == 'Ollama is running'
    except Exception:
        return False


__all__ = ['app', 'initialize', 'is_ready']
