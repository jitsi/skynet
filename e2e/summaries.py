import asyncio

from skynet.logs import get_logger
from .common import get, post

log = get_logger(__name__)

# courtesy of https://www.gutenberg.org/files/2701/2701-h/2701-h.htm#link2HCH0001
moby_dick_text = 'Call me Ishmael. Some years ago—never mind how long precisely—having little or no money in my purse, and nothing particular to interest me on shore, I thought I would sail about a little and see the watery part of the world. It is a way I have of driving off the spleen and regulating the circulation. Whenever I find myself growing grim about the mouth; whenever it is a damp, drizzly November in my soul; whenever I find myself involuntarily pausing before coffin warehouses, and bringing up the rear of every funeral I meet; and especially whenever my hypos get such an upper hand of me, that it requires a strong moral principle to prevent me from deliberately stepping into the street, and methodically knocking people’s hats off—then, I account it high time to get to sea as soon as I can. This is my substitute for pistol and ball. With a philosophical flourish Cato throws himself upon his sword; I quietly take to the ship. There is nothing surprising in this. If they but knew it, almost all men in their degree, some time or other, cherish very nearly the same feelings towards the ocean with me.'


async def create_summary():
    summary_job = {'hint': 'text', 'text': moby_dick_text}

    resp = await post('summaries/v1/summary', json=summary_job)
    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')

    return await resp.json()


async def create_action_items():
    action_items_job = {'hint': 'text', 'text': moby_dick_text}

    resp = await post('summaries/v1/action-items', json=action_items_job)
    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')

    return await resp.json()


async def create_process_text():
    action_items_job = {'prompt': 'Who is the main character in the story?', 'text': moby_dick_text}

    resp = await post('summaries/v1/action-items', json=action_items_job)
    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')

    return await resp.json()


async def get_job_result(job_id):
    resp = await get(f'summaries/v1/job/{job_id}')
    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')
    result = await resp.json()
    status = result.get('status')

    if status in ['running', 'pending']:
        await asyncio.sleep(1)
        return await get_job_result(job_id=job_id)

    assert status == 'success', log.error(f'Unexpected status: {status}')
    log.info(f'Response: {result.get("result")}')


async def run():
    log.info('#### Running summaries e2e tests')

    log.info('POST summaries/v1/summary - create a new summarisation job')
    job = await create_summary()
    job_id = job.get('id')
    log.info(f'GET summaries/v1/job/{job_id} - get the result of the summarisation job')
    await get_job_result(job_id)

    log.info('POST summaries/v1/action-items - create a new action items job')
    job = await create_action_items()
    job_id = job.get('id')
    log.info(f'GET summaries/v1/job/{job_id} - get the result of the action items job')
    await get_job_result(job_id)

    log.info('POST summaries/v1/process-text - create a new process text job')
    job = await create_process_text()
    job_id = job.get('id')
    log.info(f'GET summaries/v1/job/{job_id} - get the result of the process text job')
    await get_job_result(job_id)
