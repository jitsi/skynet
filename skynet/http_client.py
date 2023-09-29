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

async def get(url):
    async with _get_session() as session:
        async with session.get(url) as response:
            return await response.text()


__all__ = [ 'get' ]
