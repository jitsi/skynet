from e2e.transcripts import french_transcript, italian_transcript


class TestIdentifyLanguage:
    """Tests for fastText-based language identification, run against the real model."""

    def test_identifies_multiline_transcript(self):
        """Transcripts span many lines; fastText rejects newlines, so they must be handled."""
        from skynet.modules.ttt.language_id import identify_language

        assert '\n' in french_transcript

        code, confidence = identify_language(french_transcript)

        assert code == 'fr'
        assert confidence > 0.9

    def test_returns_two_letter_code_for_supported_language(self):
        from skynet.modules.ttt.language_id import identify_language

        code, _ = identify_language(italian_transcript)

        assert code == 'it'

    def test_returns_model_code_for_other_languages(self):
        """Languages Skynet has no locale for come back as-is, so callers can tell them apart."""
        from skynet.modules.ttt.language_id import identify_language

        code, confidence = identify_language('Bom dia, vamos começar a reunião sobre o orçamento do próximo trimestre.')

        assert code == 'por'
        assert confidence > 0.9

    def test_returns_none_when_model_is_missing(self, mocker, tmp_path):
        from skynet.modules.ttt import language_id

        mocker.patch.object(language_id, 'language_id_model_path', str(tmp_path / 'missing.ftz'))

        assert language_id.identify_language('Bonjour à tous') is None
