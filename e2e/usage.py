import asyncio
import os

from aiohttp import web

from skynet.logs import get_logger
from .common import get_session, post
from .summaries import get_job_result
from .transcripts import moby_dick_text

log = get_logger(__name__)

customer_id = 'e2e-usage-customer'
metrics_url = os.environ.get('E2E_METRICS_URL', 'http://localhost:8001/metrics')
usage_stub_port = int(os.environ.get('E2E_USAGE_STUB_PORT', 8899))
usage_enabled = os.environ.get('AI_STUDIO_USAGE_ENABLED', '').lower() in ['y', 'yes', 'true', '1']
usage_token = os.environ.get('AI_STUDIO_USAGE_TOKEN', 'e2e-token')
usage_channel = os.environ.get('AI_STUDIO_USAGE_CHANNEL', 'skynet_summary')

# usage events received by the AI Studio stub, in arrival order
received_events = []


async def _handle_usage(request):
    received_events.append({'authorization': request.headers.get('Authorization'), 'payload': await request.json()})
    return web.json_response({'success': True})


async def start_usage_stub():
    """Start a local stand-in for AI Studio's usage endpoint."""
    app = web.Application()
    app.router.add_post('/usage', _handle_usage)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', usage_stub_port)
    await site.start()

    return runner


async def create_summary_job():
    # Mirror the payload of the passing summaries e2e jobs and cap the output so
    # the job can never outlive JOB_TIMEOUT on a slow CPU-only runner (skynet
    # exits the whole process when a local job times out).
    resp = await post(
        f'summaries/v1/summary?customerId={customer_id}',
        json={'hint': 'text', 'text': moby_dick_text, 'max_completion_tokens': 512},
    )
    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')

    return await resp.json()


async def get_token_metric_total(direction):
    resp = await get_session().get(metrics_url)
    assert resp.status == 200, log.error(f'Unexpected metrics status code: {resp.status}')
    text = await resp.text()

    total = 0.0
    for line in text.splitlines():
        if (
            line.startswith('Skynet_Summaries_summary_tokens_total')
            and f'customer_id="{customer_id}"' in line
            and f'direction="{direction}"' in line
        ):
            total += float(line.rsplit(' ', 1)[-1])

    return total


async def wait_for_usage_event(job_id, timeout=15):
    """The usage report is fire-and-forget, so poll the stub briefly after job completion."""
    for _ in range(timeout * 2):
        for event in received_events:
            if event['payload'].get('interaction_id') == job_id:
                return event
        await asyncio.sleep(0.5)

    return None


async def test_prometheus_token_metrics():
    log.info('Testing that a summary job increments the summary_tokens metric')

    input_before = await get_token_metric_total('input')
    output_before = await get_token_metric_total('output')

    job = await create_summary_job()
    await get_job_result(job.get('id'))

    input_after = await get_token_metric_total('input')
    output_after = await get_token_metric_total('output')

    assert input_after > input_before, log.error(
        f'Expected input token metric to increase, got {input_before} -> {input_after}'
    )
    assert output_after > output_before, log.error(
        f'Expected output token metric to increase, got {output_before} -> {output_after}'
    )
    log.info(f'Token metrics test passed (input: {input_after - input_before}, output: {output_after - output_before})')


async def test_ai_studio_usage_report():
    if not usage_enabled:
        log.info('Skipping AI Studio usage report test (AI_STUDIO_USAGE_ENABLED not set)')
        return

    log.info('Testing that a completed job reports its token usage to the AI Studio stub')

    job = await create_summary_job()
    job_id = job.get('id')
    await get_job_result(job_id)

    event = await wait_for_usage_event(job_id)
    assert event is not None, log.error(f'No usage event received for job {job_id}')

    assert event['authorization'] == f'Bearer {usage_token}', log.error(
        f'Unexpected authorization header: {event["authorization"]}'
    )

    payload = event['payload']
    assert payload.get('tenant_id') == customer_id, log.error(f'Unexpected tenant_id: {payload.get("tenant_id")}')
    assert payload.get('channel') == usage_channel, log.error(f'Unexpected channel: {payload.get("channel")}')
    assert payload.get('provider') == 'local', log.error(f'Unexpected provider: {payload.get("provider")}')
    assert payload.get('event_type') == 'summary', log.error(f'Unexpected event_type: {payload.get("event_type")}')
    assert payload.get('model'), log.error('Expected a model name in the usage payload')
    assert payload.get('input_tokens', 0) > 0, log.error(f'Expected input tokens, got {payload.get("input_tokens")}')
    assert payload.get('output_tokens', 0) > 0, log.error(f'Expected output tokens, got {payload.get("output_tokens")}')

    log.info(f'AI Studio usage report test passed (payload: {payload})')


async def run():
    log.info('#### Running usage reporting e2e tests')

    stub = await start_usage_stub()

    try:
        await test_prometheus_token_metrics()
        await test_ai_studio_usage_report()
    finally:
        await stub.cleanup()
