import os
import pathlib
import time

import jwt

from hashlib import sha256
from pathlib import Path

from fastapi import HTTPException
from skynet import http_client
from skynet.env import asap_pub_keys_url, asap_pub_keys_folder, asap_pub_keys_auds, asap_cache_folder, asap_cache_ttl
from skynet.logs import get_logger

log = get_logger(__name__)


async def write_cache(path, contents):
    path = Path(f'{os.getcwd()}/{asap_cache_folder}/{path}')
    folders = path.parent.absolute()
    os.makedirs(folders, exist_ok=True)
    with open(path.absolute(), 'w') as f:
        f.write(contents)


async def get_from_cache(path: str) -> str | None:
    abs_path = f'{os.getcwd()}/{asap_cache_folder}/{path}'
    if os.path.isfile(abs_path):
        cached_file = pathlib.Path(abs_path)
        cache_age = time.time() - cached_file.stat().st_mtime
        if cache_age < asap_cache_ttl:
            with open(abs_path, 'r') as f:
                log.debug(f'Cache hit for asap path {path}')
                return f.read()
    log.debug(f'No valid cache entry for asap path {path}')
    return None


async def get_from_remote(path: str) -> str:
    requests_url = f'{asap_pub_keys_url}/{path}'
    log.debug(f'Getting remote key {requests_url}')
    try:
        pub_key = await http_client.get(requests_url)
        log.debug(pub_key)
        await write_cache(path, pub_key)
        return pub_key
    except Exception as e:
        log.error(f'Failed retrieving public key from {requests_url}. {e}')


async def get_public_key(path: str) -> str:
    cached_result = await get_from_cache(path)
    if cached_result is not None:
        return cached_result
    return await get_from_remote(path)


async def authorize(jwt_incoming: str) -> bool:
    try:
        token_header = jwt.get_unverified_header(jwt_incoming)
    except Exception:
        raise HTTPException(status_code=401, detail='Failed to decode JWT header')

    if 'kid' not in token_header:
        raise HTTPException(status_code=401, detail='Invalid token. No kid header.')

    kid = token_header["kid"]
    is_jaas = kid.startswith('vpaas-magic-cookie')
    tenant = kid.split('/')[0] if is_jaas else None
    folder = f'vpaas/{asap_pub_keys_folder}/{tenant}' if is_jaas else asap_pub_keys_folder
    encoded_pub_key_name = sha256(kid.encode('UTF-8')).hexdigest()
    pub_key_remote_filename = f'{encoded_pub_key_name}.pem'

    try:
        public_key = await get_public_key(f'{folder}/{pub_key_remote_filename}')
    except Exception:
        raise HTTPException(status_code=401, detail=f'Failed to retrieve public key. {pub_key_remote_filename}')

    try:
        jwt.decode(jwt_incoming, public_key, algorithms=['RS256', 'HS512'], audience=asap_pub_keys_auds)
        return True
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Expired token.")
    except Exception:
        raise HTTPException(status_code=401, detail=f'Failed decoding JWT with public key {pub_key_remote_filename}')
