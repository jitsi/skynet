from fastapi import Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from skynet.auth.jwt import authorize


class JWTBearer(HTTPBearer):
    def __init__(self):
        super().__init__(auto_error=True)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        if credentials and await authorize(credentials.credentials):
            return credentials.credentials
