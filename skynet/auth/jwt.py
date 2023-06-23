import os
import jwt

from fastapi import HTTPException

SSO_PUBKEY = bytes(os.environ.get('SSO_PUBKEY'), 'utf-8')
SSO_ISSUER = os.environ.get('SSO_ISSUER')
SSO_ALGORITHM = os.environ.get('SSO_PUBKEY_ALGORITHM', 'RS256')

def decodeJWT(token: str) -> dict:
    try:
        decoded_token = jwt.decode(jwt=token, key=SSO_PUBKEY, algorithms=[SSO_ALGORITHM], issuer=SSO_ISSUER, options={"verify_aud": False })

        return decoded_token
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Expired token.")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token.")
