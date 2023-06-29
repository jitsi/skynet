import jwt

from fastapi import HTTPException


def decodeJWT(token: str, key: bytes, algorithms: list[str], issuer: str) -> dict:
    try:
        return jwt.decode(jwt=token, key=key, algorithms=algorithms, issuer=issuer, options={"verify_aud": False })
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Expired token.")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token.")
