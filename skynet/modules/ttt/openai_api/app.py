import subprocess
import sys

from aiohttp.client_exceptions import ClientConnectorError

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from skynet import http_client
from skynet.auth.bearer import JWTBearer
from skynet.env import bypass_auth, llama_n_ctx, llama_path, openai_api_base_url, openai_api_port, use_oci, use_vllm
from skynet.logs import get_logger
from skynet.utils import create_app, dependencies, responses

log = get_logger(__name__)

app = create_app()
whitelisted_routes = []


def initialize():
    if not use_vllm:
        return

    from vllm.entrypoints.openai.api_server import router as vllm_router

    app.include_router(vllm_router, dependencies=dependencies, responses=responses)
    whitelisted_routes.extend(['/openai/docs', '/openai/openapi.json'])

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
            str(0.95),
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
    if use_oci:
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
