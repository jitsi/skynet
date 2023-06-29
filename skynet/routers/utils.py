import os

from fastapi import APIRouter, Depends
from fastapi_versionizer.versionizer import versioned_api_route

from skynet.auth.bearer import JWTBearer


BYPASS_AUTHORIZATION = os.environ.get('BYPASS_AUTHORIZATION', "False").lower() == 'true'

if not BYPASS_AUTHORIZATION and (not os.environ.get('SSO_PUBKEY') or not os.environ.get('SSO_ISSUER')):
    raise RuntimeError('The SSO_PUBKEY and SSO_ISSUER environment variables must be set')

def get_router(major_version: int) -> APIRouter:
    return APIRouter(
        dependencies=[] if BYPASS_AUTHORIZATION else [Depends(JWTBearer())],
        responses={
            401: {"description": "Invalid or expired token"},
            403: {"description": "Not enough permissions"}},
        route_class=versioned_api_route(major=major_version)
    )
