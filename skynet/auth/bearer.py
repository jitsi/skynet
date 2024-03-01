from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from skynet.auth.jwt import authorize
from skynet.env import app_uuid


class JWTBearer(HTTPBearer):
    def __init__(self):
        super().__init__(auto_error=True)

    async def __call__(self, request: Request):
        if request.headers.get('X-Skynet-UUID') == app_uuid:
            return None

        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        request.state.decoded_jwt = await authorize(credentials.credentials)

        return credentials.credentials
