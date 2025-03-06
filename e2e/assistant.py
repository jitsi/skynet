import asyncio

from skynet.logs import get_logger

from .common import delete, get, post, sleep_progress

log = get_logger(__name__)


async def get_rag():
    resp = await get('assistant/v1/rag')
    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')


async def create_rag():
    data = {
        'max_depth': 1,
        'urls': ['https://jitsi.github.io/handbook/docs/user-guide/user-guide-share-a-jitsi-meeting/'],
    }
    resp = await post('assistant/v1/rag', data)
    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')


async def delete_rag():
    resp = await delete('assistant/v1/rag')
    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')


async def assist():
    data = {
        'prompt': 'Tell me as short as possible, how can I share a meeting?',
        'text': '',
        'use_only_rag_data': True,
    }

    resp = await post('assistant/v1/assist', data)
    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')

    resp_json = await resp.json()
    text = resp_json.get('text')
    log.info(f'Response: {text}')

    verification = {
        'prompt': f'If I want to share a meeting can I do it like this: {text}? Respond with "yes" or "no".',
        'text': '',
    }

    resp = await post('assistant/v1/assist', verification)
    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')

    resp_json = await resp.json()
    text = resp_json.get('text')
    log.info(f'Response verification: {text}')

    assert 'yes' in text.lower(), log.error(f'Unexpected response: {text}')


async def run():
    log.info('#### Running assistant e2e tests')

    log.info('POST assistant/v1/rag - create a new RAG')
    await create_rag()

    await sleep_progress(2, 'Waiting for RAG to be created')

    log.info('GET assistant/v1/rag - RAG exists')
    await get_rag()

    log.info('POST assistant/v1/assist - ask a question')
    await assist()

    log.info('DELETE assistant/v1/rag - delete the RAG')
    await delete_rag()

    return True
