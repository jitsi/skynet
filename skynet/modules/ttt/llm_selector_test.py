import pytest

from skynet.modules.ttt.llm_selector import DEFAULT_OPENAI_CONTEXT_WINDOW, LLMSelector


def _openai_credentials(model, language_detection_model=None):
    metadata = {'model': model}
    if language_detection_model:
        metadata['languageDetectionModel'] = language_detection_model

    return {'secret': 'secret', 'type': 'OPENAI', 'metadata': metadata}


@pytest.fixture
def chat_openai(mocker):
    mocker.patch('skynet.modules.ttt.llm_selector.attach_usage_callback', side_effect=lambda llm: llm)
    return mocker.patch('skynet.modules.ttt.llm_selector.ChatOpenAI')


class TestOpenAITemperature:
    @pytest.mark.parametrize('model', ['gpt-5.4-nano', 'gpt-5-mini', 'gpt-6-luna', 'gpt-6-sol'])
    def test_fixed_temperature_models_use_default(self, mocker, chat_openai, model):
        mocker.patch('skynet.modules.ttt.llm_selector.get_credentials', return_value=_openai_credentials(model))

        LLMSelector.select('customer', temperature=0)

        assert chat_openai.call_args.kwargs['temperature'] == 1

    @pytest.mark.parametrize('model', ['gpt-4.1-mini', 'gpt-4o'])
    def test_other_models_keep_requested_temperature(self, mocker, chat_openai, model):
        mocker.patch('skynet.modules.ttt.llm_selector.get_credentials', return_value=_openai_credentials(model))

        LLMSelector.select('customer', temperature=0)

        assert chat_openai.call_args.kwargs['temperature'] == 0

    def test_language_detection_model_is_checked(self, mocker, chat_openai):
        mocker.patch(
            'skynet.modules.ttt.llm_selector.get_credentials',
            return_value=_openai_credentials('gpt-4o', language_detection_model='gpt-6-luna'),
        )

        LLMSelector.select('customer', temperature=0, for_language_detection=True)

        assert chat_openai.call_args.kwargs['model_name'] == 'gpt-6-luna'
        assert chat_openai.call_args.kwargs['temperature'] == 1


class TestOpenAIContextWindow:
    @pytest.mark.parametrize(
        'model, expected',
        [
            ('gpt-6-luna', 400000),
            ('gpt-5.4-nano', 400000),
            ('gpt-4.1-mini', 128000),
            ('some-unknown-model', DEFAULT_OPENAI_CONTEXT_WINDOW),
        ],
    )
    def test_context_window_by_family(self, mocker, model, expected):
        mocker.patch('skynet.modules.ttt.llm_selector.get_credentials', return_value=_openai_credentials(model))

        assert LLMSelector.get_context_window('customer') == expected
