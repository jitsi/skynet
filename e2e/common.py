import asyncio
from argparse import ArgumentParser, BooleanOptionalAction

import aiohttp
from tqdm import tqdm


session = None
parser = ArgumentParser()
parser.add_argument('-u', '--url', dest='url', help='skynet url', default='http://localhost:8000')
parser.add_argument('-jwt', '--jwt', dest='jwt', help='jwt token', default=None)
parser.add_argument(
    '-skip-smart-tests',
    '--skip-smart-tests',
    dest='skip_smart_tests',
    help='skip tests that require bigger models',
    action=BooleanOptionalAction,
)
parser.add_argument(
    '-modules',
    '--modules',
    dest='modules',
    help='modules to run e2e on',
    default='assistant,summaries',
)

args = parser.parse_args()
skip_smart_tests = args.skip_smart_tests
base_url = args.url
jwt = args.jwt
modules = args.modules.split(',')


def get_session():
    global session

    if session is None:
        session = aiohttp.ClientSession(headers={'Authorization': f'Bearer {jwt}'} if jwt else {})

    return session


async def close_session():
    if session is not None:
        await session.close()


async def post(path, data):
    url = f'{base_url}/{path}'

    return await get_session().post(url, json=data)


async def get(path):
    url = f'{base_url}/{path}'

    return await get_session().get(url)


async def delete(path):
    url = f'{base_url}/{path}'

    return await get_session().delete(url)


async def sleep_progress(seconds, description):
    for _ in tqdm(range(seconds), desc=description):
        await asyncio.sleep(1)


__all__ = ['close_session', 'delete', 'get', 'post', 'sleep_progress']
