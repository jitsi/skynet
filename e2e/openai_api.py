from skynet.logs import get_logger

from .common import post

log = get_logger(__name__)


async def test_chat_completion_response_format():
    """Test that /v1/chat/completions returns content as a string, not structured blocks.

    This catches regressions where use_responses_api=True causes the response
    to contain structured content blocks instead of plain strings.
    """
    data = {
        'messages': [{'role': 'user', 'content': 'Say "hello" and nothing else.'}],
        'max_completion_tokens': 10,
    }

    resp = await post('openai/v1/chat/completions?customerId=e2e', json=data)
    assert resp.status == 200, log.error(f'Unexpected status code: {resp.status}')

    result = await resp.json()
    content = result.get('choices', [{}])[0].get('message', {}).get('content')

    assert content is not None, log.error('Response content is None')
    assert isinstance(content, str), log.error(
        f'Response content should be a string, got {type(content).__name__}: {content}'
    )

    log.info(f'Response content: {content}')


async def run():
    log.info('#### Running OpenAI API e2e tests')

    log.info('POST openai/v1/chat/completions - verify response format')
    await test_chat_completion_response_format()
