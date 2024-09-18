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


async def get(url, type='json'):
    session = _get_session()
    async with session.get(url) as response:
        if type == 'json':
            return await response.json()

        return await response.text()


__all__ = ['get']
