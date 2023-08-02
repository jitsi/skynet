import jwt
import logging
import requests

from hashlib import sha256

from fastapi import HTTPException
from skynet.env import asap_pub_keys_url

def get_public_key(url: str) -> str:
    requests_url = f'{asap_pub_keys_url}/{url}'
    logging.debug(f'Getting remote key {requests_url}')

    req = requests.get(requests_url)
    pub_key = req.text

    return pub_key

def authorize(jwt_incoming: str) -> bool:
    try:
        token_header = jwt.get_unverified_header(jwt_incoming)
    except Exception:
        raise HTTPException(status_code=401, detail='Failed to decode JWT header')

    if 'kid' not in token_header:
        raise HTTPException(status_code=401, detail="Invalid token. No kid header.")

    encoded_pub_key_name = sha256((token_header["kid"] + '\n').encode('UTF-8')).hexdigest()
    pub_key_remote_filename = f'{encoded_pub_key_name}.pem'

    try:
        public_key = get_public_key(pub_key_remote_filename)
    except Exception:
        raise HTTPException(status_code=401, detail=f'Failed to retrieve public key. {pub_key_remote_filename}')

    try:
        jwt.decode(jwt_incoming, public_key, algorithms=['RS256', 'HS512'])
        return True
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Expired token.")
    except Exception:
        raise HTTPException(status_code=401, detail=f'Failed decoding JWT with public key {pub_key_remote_filename}')
