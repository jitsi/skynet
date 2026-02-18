import asyncio
import re

from skynet.logs import get_logger
from .common import get, post

log = get_logger(__name__)


def contains_chinese(text: str) -> bool:
    """Check if text contains Chinese characters."""
    return bool(re.search(r'[\u4e00-\u9fff]', text))


# courtesy of https://www.gutenberg.org/files/2701/2701-h/2701-h.htm#link2HCH0001
moby_dick_text = 'Call me Ishmael. Some years ago—never mind how long precisely—having little or no money in my purse, and nothing particular to interest me on shore, I thought I would sail about a little and see the watery part of the world. It is a way I have of driving off the spleen and regulating the circulation. Whenever I find myself growing grim about the mouth; whenever it is a damp, drizzly November in my soul; whenever I find myself involuntarily pausing before coffin warehouses, and bringing up the rear of every funeral I meet; and especially whenever my hypos get such an upper hand of me, that it requires a strong moral principle to prevent me from deliberately stepping into the street, and methodically knocking people’s hats off—then, I account it high time to get to sea as soon as I can. This is my substitute for pistol and ball. With a philosophical flourish Cato throws himself upon his sword; I quietly take to the ship. There is nothing surprising in this. If they but knew it, almost all men in their degree, some time or other, cherish very nearly the same feelings towards the ocean with me.'

# English transcript with Chinese names - should be summarized in English
mixed_language_transcript = """
张伟 (Zhang Wei): Good morning everyone, let's start the meeting.
李娜 (Li Na): Thanks Zhang Wei. I wanted to discuss the Q4 roadmap today.
王芳 (Wang Fang): Sure, I've prepared the slides. We need to focus on three main areas.
张伟 (Zhang Wei): Perfect. Let's start with the infrastructure updates.
李娜 (Li Na): Our team has completed the migration to the new cloud provider. Performance improved by 40%.
王芳 (Wang Fang): That's great news. What about the security audit?
张伟 (Zhang Wei): The audit is scheduled for next week. 陈明 (Chen Ming) will be leading that effort.
李娜 (Li Na): We should also discuss the budget allocation for the new hires.
王芳 (Wang Fang): I agree. We need at least three more engineers for the mobile team.
张伟 (Zhang Wei): Let's schedule a follow-up meeting to finalize the budget. Thanks everyone for joining today.
"""


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

    return result


async def create_summary_mixed_language():
    """Create a summary job with a mostly-English transcript containing Chinese names."""
    summary_job = {'hint': 'meeting', 'text': mixed_language_transcript}

    resp = await post('summaries/v1/summary', json=summary_job)
    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')

    return await resp.json()


async def test_summary_language_detection():
    """Test that a mostly-English transcript with Chinese names is summarized in English."""
    log.info('POST summaries/v1/summary - create summary for mixed-language transcript')
    job = await create_summary_mixed_language()
    job_id = job.get('id')

    log.info(f'GET summaries/v1/job/{job_id} - get the result')
    result = await get_job_result(job_id)

    summary_text = result.get('result', '')
    assert not contains_chinese(summary_text), log.error(
        f'Summary should be in English but contains Chinese characters: {summary_text}'
    )
    log.info('Language detection test passed - summary is in English')


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

    log.info('Testing language detection for mixed-language transcripts')
    await test_summary_language_detection()
