"""
Simple async HTTP client with a shared session. We are not going to
make requests to an arbitrarily large amount of domains so using a single
session is OK.
"""

import aiohttp


_session = None


def _get_session():
    global _session

    if _session is None:
        _session = aiohttp.ClientSession()
    return _session


async def get(url, type='json', **kwargs):
    session = _get_session()
    async with session.get(url, **kwargs) as response:
        if type == 'json':
            return await response.json()

        return await response.text()


async def post(url, **kwargs):
    session = _get_session()
    async with session.post(url, **kwargs) as response:
        return await response.json()


async def request(method, url, **kwargs) -> aiohttp.ClientResponse:
    session = _get_session()

    return await session.request(method, url, **kwargs)


async def close():
    if _session is not None:
        await _session.close()

        _session = None


__all__ = ['close', 'get', 'post', 'request']
