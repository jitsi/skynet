from hashlib import sha256

import jwt
from async_lru import alru_cache
from fastapi import HTTPException

from skynet import http_client
from skynet.env import (
    asap_pub_keys_auds,
    asap_pub_keys_fallback_folder,
    asap_pub_keys_folder,
    asap_pub_keys_max_cache_size,
    asap_pub_keys_url,
)
from skynet.logs import get_logger

log = get_logger(__name__)


@alru_cache(maxsize=asap_pub_keys_max_cache_size)
async def get_public_key(kid: str) -> str:
    encoded_pub_key_name = sha256(kid.encode('UTF-8')).hexdigest()
    pub_key_remote_filename = f'{encoded_pub_key_name}.pem'

    url = f'{asap_pub_keys_url}/{asap_pub_keys_folder}/{pub_key_remote_filename}'

    log.info(f'Fetching public key {kid} from {url}')
    response = await http_client.request('GET', url)

    if response.status != 200:
        error = f'Failed to retrieve public key {kid}'

        if asap_pub_keys_fallback_folder:
            url = f'{asap_pub_keys_url}/{asap_pub_keys_fallback_folder}/{pub_key_remote_filename}'

            log.info(f'Fetching public key {kid} from {url}')

            response = await http_client.request('GET', url)

            if response.status != 200:
                raise Exception(error)
        else:
            raise Exception(error)

    return await response.text()


async def authorize(jwt_incoming: str) -> dict:
    try:
        token_header = jwt.get_unverified_header(jwt_incoming)
    except Exception:
        raise HTTPException(status_code=401, detail='Failed to decode JWT header')

    if 'kid' not in token_header:
        raise HTTPException(status_code=401, detail="Invalid token. No kid header.")

    kid = token_header["kid"]

    try:
        public_key = await get_public_key(kid)
    except Exception as ex:
        raise HTTPException(status_code=401, detail=str(ex))

    try:
        decoded = jwt.decode(jwt_incoming, public_key, algorithms=['RS256', 'HS512'], audience=asap_pub_keys_auds)

        if decoded.get('appId') is None:
            decoded['appId'] = kid

        return decoded
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Expired token.")
    except Exception:
        raise HTTPException(status_code=401, detail=f'Failed decoding JWT with public key {kid}')
