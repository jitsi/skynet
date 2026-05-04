import asyncio
import re

from skynet.logs import get_logger
from .common import get, post, skip_smart_tests
from .transcripts import (
    english_transcript,
    french_transcript,
    german_transcript,
    italian_transcript,
    moby_dick_text,
    spanish_transcript,
)

log = get_logger(__name__)


def contains_french_indicators(text: str) -> bool:
    """Check if text contains French language indicators."""
    french_patterns = [
        r'\b(le|la|les|un|une|des|du|de la)\b',  # articles
        r'\b(est|sont|a|ont|été|être|avoir)\b',  # common verbs
        r'\b(nous|vous|ils|elles|ce|cette)\b',  # pronouns
        r'\b(pour|avec|dans|sur|par)\b',  # prepositions
        r'[àâäéèêëïîôùûüç]',  # French accented characters
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in french_patterns)


def contains_german_indicators(text: str) -> bool:
    """Check if text contains German language indicators."""
    german_patterns = [
        r'\b(der|die|das|ein|eine|einer)\b',  # articles
        r'\b(ist|sind|hat|haben|wurde|werden)\b',  # common verbs
        r'\b(wir|sie|es|ich|er|ihr)\b',  # pronouns
        r'\b(für|mit|auf|bei|nach|von)\b',  # prepositions
        r'[äöüßÄÖÜ]',  # German specific characters
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in german_patterns)


def contains_spanish_indicators(text: str) -> bool:
    """Check if text contains Spanish language indicators."""
    spanish_patterns = [
        r'\b(el|la|los|las|un|una|unos|unas)\b',  # articles
        r'\b(es|son|está|están|ha|han|fue|fueron)\b',  # common verbs
        r'\b(nosotros|ellos|ellas|esto|esta)\b',  # pronouns
        r'\b(para|con|sobre|por|entre)\b',  # prepositions
        r'[áéíóúñ¿¡]',  # Spanish specific characters
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in spanish_patterns)


def contains_italian_indicators(text: str) -> bool:
    """Check if text contains Italian language indicators."""
    italian_patterns = [
        r'\b(il|lo|la|i|gli|le|un|uno|una)\b',  # articles
        r'\b(è|sono|ha|hanno|stato|stata)\b',  # common verbs
        r'\b(noi|loro|questo|questa|quello)\b',  # pronouns
        r'\b(per|con|sul|nella|tra|fra)\b',  # prepositions
        r'[àèéìòù]',  # Italian accented characters
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in italian_patterns)


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


def contains_english_indicators(text: str) -> bool:
    """Check if text contains English language indicators."""
    english_patterns = [
        r'\b(the|a|an|is|are|was|were)\b',  # articles and verbs
        r'\b(and|or|but|with|for|to)\b',  # conjunctions and prepositions
        r'\b(have|has|had|will|would|could)\b',  # auxiliary verbs
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in english_patterns)


async def create_summary_for_transcript(transcript: str, hint: str = 'meeting'):
    """Create a summary job for a given transcript."""
    summary_job = {'hint': hint, 'text': transcript}

    resp = await post('summaries/v1/summary', json=summary_job)
    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')

    return await resp.json()


async def test_english_language_detection():
    """Test that an English transcript is summarized in English."""
    log.info('Testing English language detection')
    job = await create_summary_for_transcript(english_transcript)
    job_id = job.get('id')

    result = await get_job_result(job_id)
    summary_text = result.get('result', '')

    assert contains_english_indicators(summary_text), log.error(
        f'Summary should be in English but does not contain English indicators: {summary_text}'
    )
    log.info('English language detection test passed')


async def test_french_language_detection():
    """Test that a French transcript is summarized in French."""
    log.info('Testing French language detection')
    job = await create_summary_for_transcript(french_transcript)
    job_id = job.get('id')

    result = await get_job_result(job_id)
    summary_text = result.get('result', '')

    assert contains_french_indicators(summary_text), log.error(
        f'Summary should be in French but does not contain French indicators: {summary_text}'
    )
    log.info('French language detection test passed')


async def test_german_language_detection():
    """Test that a German transcript is summarized in German."""
    log.info('Testing German language detection')
    job = await create_summary_for_transcript(german_transcript)
    job_id = job.get('id')

    result = await get_job_result(job_id)
    summary_text = result.get('result', '')

    assert contains_german_indicators(summary_text), log.error(
        f'Summary should be in German but does not contain German indicators: {summary_text}'
    )
    log.info('German language detection test passed')


async def test_spanish_language_detection():
    """Test that a Spanish transcript is summarized in Spanish."""
    log.info('Testing Spanish language detection')
    job = await create_summary_for_transcript(spanish_transcript)
    job_id = job.get('id')

    result = await get_job_result(job_id)
    summary_text = result.get('result', '')

    assert contains_spanish_indicators(summary_text), log.error(
        f'Summary should be in Spanish but does not contain Spanish indicators: {summary_text}'
    )
    log.info('Spanish language detection test passed')


async def test_italian_language_detection():
    """Test that an Italian transcript is summarized in Italian."""
    log.info('Testing Italian language detection')
    job = await create_summary_for_transcript(italian_transcript)
    job_id = job.get('id')

    result = await get_job_result(job_id)
    summary_text = result.get('result', '')

    assert contains_italian_indicators(summary_text), log.error(
        f'Summary should be in Italian but does not contain Italian indicators: {summary_text}'
    )
    log.info('Italian language detection test passed')


async def run_language_detection_tests():
    """Run all language detection tests."""
    if skip_smart_tests:
        log.info('Skipping language detection tests (requires smarter models)')
        return

    log.info('#### Running language detection e2e tests')

    await test_english_language_detection()
    await test_french_language_detection()
    await test_german_language_detection()
    await test_spanish_language_detection()
    await test_italian_language_detection()

    log.info('All language detection tests passed!')


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

    log.info('Running language detection tests')
    await run_language_detection_tests()
