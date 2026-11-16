from skynet.constants import Locale
from skynet.modules.ttt.summaries.prompts.common import get_language_instruction


class TestGetLanguageInstruction:
    def test_names_locale(self):
        assert get_language_instruction(Locale.FRENCH) == 'Generate the response in french.'

    def test_names_detected_language_without_locale(self):
        assert get_language_instruction('portuguese') == 'Generate the response in portuguese.'

    def test_asks_llm_to_infer_language_when_unknown(self):
        assert 'Identify the predominant language' in get_language_instruction(None)
