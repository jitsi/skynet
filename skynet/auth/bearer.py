import os

from fastapi import Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from skynet.auth.jwt import decodeJWT

class JWTBearer(HTTPBearer):
    def __init__(self):
        super(JWTBearer, self).__init__(auto_error=True)

        self.SSO_PUBKEY = bytes(os.environ.get('SSO_PUBKEY'), 'utf-8')
        self.SSO_ISSUER = os.environ.get('SSO_ISSUER')
        self.SSO_ALGORITHM = os.environ.get('SSO_PUBKEY_ALGORITHM', 'RS256')

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)

        if credentials and decodeJWT(credentials.credentials, self.SSO_PUBKEY, [self.SSO_ALGORITHM], self.SSO_ISSUER):
            return credentials.credentials
