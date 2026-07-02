from types import SimpleNamespace

import pytest


def _response(generations=None, llm_output=None):
    """Build a minimal LLMResult-like object for _extract_usage."""
    return SimpleNamespace(generations=generations or [], llm_output=llm_output)


def _generation(input_tokens=None, output_tokens=None, model=None):
    usage = None
    if input_tokens is not None or output_tokens is not None:
        usage = {'input_tokens': input_tokens or 0, 'output_tokens': output_tokens or 0}
    message = SimpleNamespace(usage_metadata=usage, response_metadata={'model_name': model} if model else {})
    return SimpleNamespace(message=message)


class TestExtractUsage:
    def test_extracts_from_usage_metadata(self):
        from skynet.modules.ttt.usage_reporting import _extract_usage

        response = _response(generations=[[_generation(input_tokens=120, output_tokens=45, model='gpt-5')]])
        assert _extract_usage(response) == (120, 45, 'gpt-5')

    def test_sums_across_generations(self):
        from skynet.modules.ttt.usage_reporting import _extract_usage

        response = _response(
            generations=[
                [_generation(input_tokens=100, output_tokens=10)],
                [_generation(input_tokens=50, output_tokens=5)],
            ]
        )
        input_tokens, output_tokens, _ = _extract_usage(response)
        assert (input_tokens, output_tokens) == (150, 15)

    def test_falls_back_to_llm_output_token_usage(self):
        from skynet.modules.ttt.usage_reporting import _extract_usage

        response = _response(
            generations=[[_generation()]],  # no usage_metadata
            llm_output={'token_usage': {'prompt_tokens': 200, 'completion_tokens': 60}, 'model_name': 'oci-model'},
        )
        assert _extract_usage(response) == (200, 60, 'oci-model')

    def test_returns_zero_when_no_usage(self):
        from skynet.modules.ttt.usage_reporting import _extract_usage

        assert _extract_usage(_response(generations=[[_generation()]])) == (0, 0, None)


class TestUsageCollector:
    def test_accumulates_and_captures_model(self):
        from skynet.modules.ttt.usage_reporting import UsageCollector

        collector = UsageCollector(app_id='app1', customer_id='cust1', processor='OCI')
        collector.on_llm_end(_response(generations=[[_generation(input_tokens=100, output_tokens=20, model='m')]]))
        collector.on_llm_end(_response(generations=[[_generation(input_tokens=30, output_tokens=5)]]))

        assert collector.input_tokens == 130
        assert collector.output_tokens == 25
        assert collector.model == 'm'


class TestReportUsageToAiStudio:
    @pytest.mark.asyncio
    async def test_skips_when_disabled(self, mocker):
        import skynet.modules.ttt.usage_reporting as ur

        mocker.patch.object(ur, 'ai_studio_usage_enabled', False)
        http_post = mocker.patch.object(ur, 'http_post', new=mocker.AsyncMock())

        await ur.report_usage_to_ai_studio(
            customer_id='c',
            app_id='a',
            job_id='j',
            event_type='summary',
            provider='oci',
            model='m',
            input_tokens=10,
            output_tokens=5,
        )
        http_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_without_customer_id(self, mocker):
        import skynet.modules.ttt.usage_reporting as ur

        mocker.patch.object(ur, 'ai_studio_usage_enabled', True)
        mocker.patch.object(ur, 'ai_studio_usage_url', 'https://studio/api/usage')
        mocker.patch.object(ur, 'ai_studio_usage_token', 'st_x')
        http_post = mocker.patch.object(ur, 'http_post', new=mocker.AsyncMock())

        await ur.report_usage_to_ai_studio(
            customer_id=None,
            app_id='a',
            job_id='j',
            event_type='summary',
            provider='oci',
            model='m',
            input_tokens=10,
            output_tokens=5,
        )
        http_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_with_zero_tokens(self, mocker):
        import skynet.modules.ttt.usage_reporting as ur

        mocker.patch.object(ur, 'ai_studio_usage_enabled', True)
        mocker.patch.object(ur, 'ai_studio_usage_url', 'https://studio/api/usage')
        mocker.patch.object(ur, 'ai_studio_usage_token', 'st_x')
        http_post = mocker.patch.object(ur, 'http_post', new=mocker.AsyncMock())

        await ur.report_usage_to_ai_studio(
            customer_id='c',
            app_id='a',
            job_id='j',
            event_type='summary',
            provider='oci',
            model='m',
            input_tokens=0,
            output_tokens=0,
        )
        http_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_posts_expected_payload(self, mocker):
        import skynet.modules.ttt.usage_reporting as ur

        mocker.patch.object(ur, 'ai_studio_usage_enabled', True)
        mocker.patch.object(ur, 'ai_studio_usage_url', 'https://studio/api/usage')
        mocker.patch.object(ur, 'ai_studio_usage_token', 'st_x')
        mocker.patch.object(ur, 'ai_studio_usage_channel', 'skynet_summary')
        http_post = mocker.patch.object(ur, 'http_post', new=mocker.AsyncMock(return_value={'success': True}))

        await ur.report_usage_to_ai_studio(
            customer_id='cust1',
            app_id='meetings',
            job_id='job-123',
            event_type='summary',
            provider='oci',
            model='cohere.command',
            input_tokens=120,
            output_tokens=45,
        )

        http_post.assert_called_once()
        payload = http_post.call_args.args[0]
        assert payload == {
            'tenant_id': 'cust1',
            'channel': 'skynet_summary',
            'provider': 'oci',
            'model': 'cohere.command',
            'event_type': 'summary',
            'agent_name': 'meetings',
            'interaction_id': 'job-123',
            'input_tokens': 120,
            'output_tokens': 45,
        }
