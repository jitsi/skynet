import asyncio

from skynet.logs import get_logger
from skynet.modules.ttt.assistant.v1.models import RagStatus

from .common import delete, get, post, skip_smart_tests

log = get_logger(__name__)


async def get_rag():
    resp = await get('assistant/v1/rag?customerId=e2e')

    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')

    result = await resp.json()
    status = result.get('status')

    if status == RagStatus.RUNNING.value:
        await asyncio.sleep(1)
        return await get_rag()

    assert status == RagStatus.SUCCESS.value, log.error(f'Unexpected status: {status}')
    log.info(f'RAG Config: {result}')


async def create_rag():
    data = {
        'max_depth': 1,
        'urls': ['https://jitsi.github.io/handbook/docs/user-guide/user-guide-share-a-jitsi-meeting/'],
    }
    resp = await post('assistant/v1/rag?customerId=e2e', json=data)
    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')


async def delete_rag():
    resp = await delete('assistant/v1/rag?customerId=e2e')
    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')


async def assist():
    data = {
        'prompt': 'Tell me as short as possible, how can I share a meeting?',
        'text': '',
        'use_only_rag_data': True,
    }

    resp = await post('assistant/v1/assist?customerId=e2e', json=data)
    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')

    resp_json = await resp.json()
    text = resp_json.get('text')
    log.info(f'Response: {text}')

    if skip_smart_tests:
        return

    verification = {
        'prompt': f'If I want to share a meeting can I do it like this: {text}? Respond with "yes" or "no".',
        'text': '',
    }

    resp = await post('assistant/v1/assist?customerId=e2e', json=verification)
    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')

    resp_json = await resp.json()
    text = resp_json.get('text')
    log.info(f'Response verification: {text}')

    assert 'yes' in text.lower(), log.error(f'Unexpected response: {text}')


async def run():
    log.info('#### Running assistant e2e tests')

    log.info('POST assistant/v1/rag?customerId=e2e - create a new RAG')
    await create_rag()

    log.info('GET assistant/v1/rag?customerId=e2e - RAG exists')
    await get_rag()

    log.info('POST assistant/v1/assist?customerId=e2e - ask a question')
    await assist()

    log.info('DELETE assistant/v1/rag?customerId=e2e - delete the RAG')
    await delete_rag()

    return True
