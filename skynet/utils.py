from fastapi import APIRouter, Depends
from fastapi_versionizer.versionizer import versioned_api_route
import uvicorn

from skynet.auth.bearer import JWTBearer
from skynet.env import bypass_auth
from skynet.logs import uvicorn_log_config

dependencies = [] if bypass_auth else [Depends(JWTBearer())]
responses = (
    {}
    if bypass_auth
    else {401: {"description": "Invalid or expired token"}, 403: {"description": "Not enough permissions"}}
)


def get_router(major_version: int) -> APIRouter:
    return APIRouter(
        dependencies=dependencies, responses=responses, route_class=versioned_api_route(major=major_version)
    )


async def create_webserver(app, port):
    server_config = uvicorn.Config(app, port=port, log_config=uvicorn_log_config)
    server = uvicorn.Server(server_config)
    await server.serve()
