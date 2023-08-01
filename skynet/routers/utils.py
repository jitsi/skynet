import os

from fastapi import APIRouter, Depends
from fastapi_versionizer.versionizer import versioned_api_route

from skynet.auth.bearer import JWTBearer
from skynet.env import bypass_auth

def get_router(major_version: int) -> APIRouter:
    return APIRouter(
        dependencies=[] if bypass_auth else [Depends(JWTBearer())],
        responses={
            401: {"description": "Invalid or expired token"},
            403: {"description": "Not enough permissions"}},
        route_class=versioned_api_route(major=major_version)
    )
