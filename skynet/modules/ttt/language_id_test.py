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

    def test_returns_model_label_with_script_for_other_languages(self):
        """Languages Skynet has no locale for come back as the model's label, script included."""
        from skynet.modules.ttt.language_id import identify_language

        code, confidence = identify_language('Bom dia, vamos começar a reunião sobre o orçamento do próximo trimestre.')

        assert code == 'por_Latn'
        assert confidence > 0.9

    def test_returns_none_when_model_is_missing(self, mocker, tmp_path):
        from skynet.modules.ttt import language_id

        mocker.patch.object(language_id, 'language_id_model_path', str(tmp_path / 'missing.ftz'))

        assert language_id.identify_language('Bonjour à tous') is None


class TestLanguageName:
    """Only major languages, in their usual script, get named in prompts."""

    def test_names_well_supported_language(self):
        from skynet.modules.ttt.language_id import language_name

        assert language_name('por_Latn') == 'portuguese'
        assert language_name('jpn_Jpan') == 'japanese'

    def test_skips_minor_languages_and_dialects(self):
        """GlotLID can mistake a messy meeting for a regional variety; naming that would mislead the LLM."""
        from skynet.modules.ttt.language_id import language_name

        assert language_name('lmo_Latn') is None  # Lombard
        assert language_name('pcd_Latn') is None  # Picard

    def test_skips_romanized_scripts(self):
        """Romanized Hindi should not turn into a Devanagari summary."""
        from skynet.modules.ttt.language_id import language_name

        assert language_name('hin_Latn') is None
        assert language_name('hin_Deva') == 'hindi'
