from argparse import ArgumentParser

import aiohttp


session = None
parser = ArgumentParser()
parser.add_argument('-u', '--url', dest='url', help='skynet url', default='http://localhost:8000')
parser.add_argument('-jwt', '--jwt', dest='jwt', help='jwt token', default=None)
parser.add_argument(
    '-modules',
    '--modules',
    dest='modules',
    help='modules to run e2e on',
    default='assistant,summaries:dispatcher,summaries:executor',
)

args = parser.parse_args()
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


__all__ = ['delete', 'get', 'post']
