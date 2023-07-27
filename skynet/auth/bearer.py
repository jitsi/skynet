import os

from fastapi import Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from skynet.auth.jwt import decodeJWT
from skynet.env import sso_issuer, sso_pubkey, sso_algorithm

class JWTBearer(HTTPBearer):
    def __init__(self):
        super().__init__(auto_error=True)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        if credentials and decodeJWT(credentials.credentials, sso_pubkey, [sso_algorithm], sso_issuer):
            return credentials.credentials
