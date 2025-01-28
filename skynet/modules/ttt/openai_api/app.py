import subprocess
import sys
from enum import Enum

from aiohttp.client_exceptions import ClientConnectorError

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from vllm.entrypoints.openai.api_server import router as vllm_router

from skynet import http_client
from skynet.auth.bearer import JWTBearer
from skynet.env import bypass_auth, openai_api_base_url, use_vllm
from skynet.logs import get_logger
from skynet.utils import create_app, dependencies, responses

log = get_logger(__name__)


class TaskType(Enum):
    GENERATE = 'generate'
    EMBEDDING = 'embedding'


def initialize(model_path: str, max_model_len: int, port: int, task: TaskType):
    if not use_vllm:
        return

    log.info(f'Starting vLLM server for {task.value} task on port {port} using model {model_path}')

    gpu_memory_utilization = 0.88 if task == TaskType.GENERATE else 0.1
    # cpu_offload_gb = 4 if task == TaskType.EMBEDDING else 0

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "vllm.entrypoints.openai.api_server",
            "--trust-remote-code",
            # "--cpu-offload-gb", str(cpu_offload_gb),
            "--disable-log-requests",
            "--model",
            model_path,
            "--task",
            task.value,
            "--gpu_memory_utilization",
            str(gpu_memory_utilization),
            "--max-model-len",
            str(max_model_len),
            "--port",
            str(port),
        ],
        shell=False,
    )

    if proc.poll() is not None:
        log.error('Failed to start vLLM OpenAI API server')
    else:
        log.info('vLLM OpenAI API server started')


async def is_ready():
    url = f'{openai_api_base_url}/health' if use_vllm else openai_api_base_url

    try:
        response = await http_client.get(url, 'text')

        if use_vllm:
            return response == ''
        else:
            return response == 'Ollama is running'
    except Exception:
        return False


app = create_app()
app.include_router(vllm_router, dependencies=dependencies, responses=responses)

whitelisted_routes = ['/openai/docs', '/openai/openapi.json']

bearer = JWTBearer()


@app.middleware('http')
async def proxy_middleware(request: Request, call_next):
    if request.url.path in whitelisted_routes:
        return await call_next(request)

    if not bypass_auth:
        try:
            await bearer.__call__(request)
        except HTTPException as e:
            return JSONResponse(content=responses.get(e.status_code), status_code=e.status_code)

    try:
        url = f'{openai_api_base_url}{request.url.path.replace("/openai", "")}'
        response = await http_client.request(request.method, url, headers=request.headers, data=await request.body())

        return StreamingResponse(response.content, status_code=response.status, headers=response.headers)
    except ClientConnectorError as e:
        return JSONResponse(content=str(e), status_code=500)
    except HTTPException as e:
        return JSONResponse(content=e.detail, status_code=e.status_code)
    except Exception as e:
        return JSONResponse(content=str(e), status_code=500)


__all__ = ['app', 'initialize', 'is_ready']
