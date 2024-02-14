import os

import uvicorn
from fastapi import APIRouter, Depends

from skynet.auth.bearer import JWTBearer
from skynet.env import bypass_auth, bypass_openai_api_auth
from skynet.logs import get_logger, uvicorn_log_config
from skynet.modules.monitoring import FORCED_EXIT_COUNTER

log = get_logger(__name__)

dependencies = [] if bypass_auth else [Depends(JWTBearer())]
openai_api_dependencies = [] if bypass_openai_api_auth else [Depends(JWTBearer())]

responses = (
    {}
    if bypass_auth
    else {401: {"description": "Invalid or expired token"}, 403: {"description": "Not enough permissions"}}
)


def get_router() -> APIRouter:
    return APIRouter(dependencies=dependencies, responses=responses)


async def create_webserver(app, port):
    server_config = uvicorn.Config(app, host='0.0.0.0', port=port, log_config=uvicorn_log_config)
    server = uvicorn.Server(server_config)
    await server.serve()


def kill_process():
    log.info('Killing current process')

    FORCED_EXIT_COUNTER.inc()

    os._exit(1)
