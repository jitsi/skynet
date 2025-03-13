import asyncio

from aiohttp import FormData

from skynet.logs import get_logger
from skynet.modules.ttt.assistant.v1.models import RagStatus

from .common import delete, get, post, skip_smart_tests

log = get_logger(__name__)

test_file_name = 'test_readme.txt'


def create_file(filename, content):
    with open(filename, 'w') as f:
        f.write(content)


def delete_file(filename):
    import os

    os.remove(filename)


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
    form = FormData()
    form.add_field('max_depth', '1')
    create_file(
        test_file_name, 'Skynet is an API service for summarisation, RAG assistance, real time transcriptions and more'
    )
    form.add_field('files', open('test_readme.txt', 'r'))
    form.add_field('urls', 'https://jitsi.github.io/handbook/docs/user-guide/user-guide-share-a-jitsi-meeting')
    resp = await post('assistant/v1/rag?customerId=e2e', data=form)
    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')


async def delete_rag():
    resp = await delete('assistant/v1/rag?customerId=e2e')

    delete_file(test_file_name)

    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')


async def get_assist(data):
    resp = await post('assistant/v1/assist?customerId=e2e', json=data)
    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')

    resp_json = await resp.json()
    text = resp_json.get('text')

    return text


async def assist_from_url():
    prompt = 'Tell me as short as possible, how can I share a meeting?'
    data = {
        'prompt': prompt,
        'text': '',
        'use_only_rag_data': True,
    }

    log.info(f'Question: {prompt}')
    text = await get_assist(data)
    log.info(f'Response: {text}')

    if skip_smart_tests:
        return

    prompt = f'If I want to share a meeting can I do it like this: {text} Respond with "yes" or "no".'
    verification = {
        'prompt': prompt,
        'text': '',
        'use_only_rag_data': True,
    }

    log.info(f'Verification question: {prompt}')
    text = await get_assist(verification)
    log.info(f'Response verification: {text}')

    assert 'yes' in text.lower(), log.error(f'Unexpected response: {text}')


async def assist_from_files():
    prompt = 'Tell me as short as possible, what is Skynet?'
    data = {
        'prompt': prompt,
        'text': '',
        'use_only_rag_data': True,
    }

    log.info(f'Question: {prompt}')
    text = await get_assist(data)
    log.info(f'Response: {text}')

    if skip_smart_tests:
        return

    prompt = f'Is this accurate: {text} Respond with "yes" or "no".'
    verification = {
        'prompt': prompt,
        'text': '',
        'use_only_rag_data': True,
    }

    log.info(f'Verification question: {prompt}')
    text = await get_assist(verification)
    log.info(f'Response verification: {text}')

    assert 'yes' in text.lower(), log.error(f'Unexpected response: {text}')


async def run():
    try:
        log.info('#### Running assistant e2e tests')

        log.info('POST assistant/v1/rag - create a new RAG')
        await create_rag()

        log.info('GET assistant/v1/rag - RAG exists')
        await get_rag()

        log.info('POST assistant/v1/assist - ask a question with the answer contained in provided urls')
        await assist_from_url()

        log.info('POST assistant/v1/assist - ask a question with the answer contained in provided files')
        await assist_from_files()
    finally:
        log.info('DELETE assistant/v1/rag - delete the RAG')
        await delete_rag()
