import asyncio

from skynet.logs import get_logger
from .common import get, post, skip_smart_tests

log = get_logger(__name__)

# courtesy of https://www.gutenberg.org/files/2701/2701-h/2701-h.htm#link2HCH0001
moby_dick_text = 'Call me Ishmael. Some years ago—never mind how long precisely—having little or no money in my purse, and nothing particular to interest me on shore, I thought I would sail about a little and see the watery part of the world. It is a way I have of driving off the spleen and regulating the circulation. Whenever I find myself growing grim about the mouth; whenever it is a damp, drizzly November in my soul; whenever I find myself involuntarily pausing before coffin warehouses, and bringing up the rear of every funeral I meet; and especially whenever my hypos get such an upper hand of me, that it requires a strong moral principle to prevent me from deliberately stepping into the street, and methodically knocking people’s hats off—then, I account it high time to get to sea as soon as I can. This is my substitute for pistol and ball. With a philosophical flourish Cato throws himself upon his sword; I quietly take to the ship. There is nothing surprising in this. If they but knew it, almost all men in their degree, some time or other, cherish very nearly the same feelings towards the ocean with me.'


async def create_summary(locale=None):
    summary_job = {'hint': 'text', 'text': moby_dick_text}
    if locale:
        summary_job['preferred_locale'] = locale

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

    return result.get("result")


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

    if skip_smart_tests:
        log.info('Skipping locale-specific tests due to skip_smart_tests flag')
        return

    log.info('POST summaries/v1/summary - create a new summarisation job with Italian locale')
    job = await create_summary('it')
    job_id = job.get('id')
    log.info(f'GET summaries/v1/job/{job_id} - get the result of the Italian summarisation job')
    result_it = await get_job_result(job_id)

    # Check for Italian words (protagonist = protagonista, navigation = navigazione)
    italian_words = ['sentimento', 'quando', 'imbarcarsi', 'narrador']
    has_italian = any(word in result_it.lower() for word in italian_words)
    assert has_italian, log.error('Italian translation not detected - expected "protagonista" or "navigazione"')
    log.info('Italian translation verified')

    log.info('POST summaries/v1/summary - create a new summarisation job with Spanish locale')
    job = await create_summary('es')
    job_id = job.get('id')
    log.info(f'GET summaries/v1/job/{job_id} - get the result of the Spanish summarisation job')
    result_es = await get_job_result(job_id)

    # Check for Spanish words (protagonist = protagonista, navigation = navegación)
    spanish_words = ['sentimiento', 'cuando', 'embarcarse', 'narrador']
    has_spanish = any(word in result_es.lower() for word in spanish_words)
    assert has_spanish, log.error('Spanish translation not detected - expected "protagonista" or "navegación"')
    log.info('Spanish translation verified')

    log.info('POST summaries/v1/summary - create a new summarisation job with French locale')
    job = await create_summary('fr')
    job_id = job.get('id')
    log.info(f'GET summaries/v1/job/{job_id} - get the result of the French summarisation job')
    result_fr = await get_job_result(job_id)

    # Check for French words (ocean = océan, character = personnage)
    french_words = ['océan', 'quand', 'personnage', 'narrateur']
    has_french = any(word in result_fr.lower() for word in french_words)
    assert has_french, log.error('French translation not detected - expected "océan" or "personnage"')
    log.info('French translation verified')

    log.info('POST summaries/v1/summary - create a new summarisation job with German locale')
    job = await create_summary('de')
    job_id = job.get('id')
    log.info(f'GET summaries/v1/job/{job_id} - get the result of the German summarisation job')
    result_de = await get_job_result(job_id)

    # Check for German words (ocean = ozean, character = charakter)
    german_words = ['ozean', 'wenn', 'charakter', 'narrator']
    has_german = any(word in result_de.lower() for word in german_words)
    assert has_german, log.error('German translation not detected - expected "ozean" or "charakter"')
    log.info('German translation verified')
