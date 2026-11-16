from functools import cache
from typing import Optional

import fasttext

from skynet.env import language_id_model_path
from skynet.logs import get_logger

log = get_logger(__name__)

# GlotLID labels are ISO 639-3 plus script (e.g. fra_Latn). Supported locales are mapped to
# the two-letter codes Skynet uses; two-letter labels from lid.176 pass through unchanged.
_ISO_639_3_TO_1 = {
    'eng': 'en',
    'fra': 'fr',
    'deu': 'de',
    'ita': 'it',
    'spa': 'es',
}

# Major languages without a Skynet Locale that the LLM is still told to answer in, keyed by GlotLID
# label in their usual script. Anything else (regional varieties, low-resource languages, romanized
# scripts) is left for the LLM to infer, since a wrong guess there would mislead it more than help.
_WELL_SUPPORTED_LANGUAGES = {
    'arb_Arab': 'arabic',
    'ben_Beng': 'bengali',
    'bul_Cyrl': 'bulgarian',
    'cat_Latn': 'catalan',
    'ces_Latn': 'czech',
    'cmn_Hani': 'chinese',
    'dan_Latn': 'danish',
    'ell_Grek': 'greek',
    'fas_Arab': 'persian',
    'fin_Latn': 'finnish',
    'heb_Hebr': 'hebrew',
    'hin_Deva': 'hindi',
    'hrv_Latn': 'croatian',
    'hun_Latn': 'hungarian',
    'ind_Latn': 'indonesian',
    'jpn_Jpan': 'japanese',
    'kor_Hang': 'korean',
    'lit_Latn': 'lithuanian',
    'nld_Latn': 'dutch',
    'nob_Latn': 'norwegian',
    'pol_Latn': 'polish',
    'por_Latn': 'portuguese',
    'ron_Latn': 'romanian',
    'rus_Cyrl': 'russian',
    'slk_Latn': 'slovak',
    'slv_Latn': 'slovenian',
    'srp_Cyrl': 'serbian',
    'srp_Latn': 'serbian',
    'swe_Latn': 'swedish',
    'tha_Thai': 'thai',
    'tur_Latn': 'turkish',
    'ukr_Cyrl': 'ukrainian',
    'urd_Arab': 'urdu',
    'vie_Latn': 'vietnamese',
    'zsm_Latn': 'malay',
}

# fastText prints a deprecation warning to stderr on every load_model call
fasttext.FastText.eprint = lambda *args, **kwargs: None


@cache
def _load_model(path: str) -> Optional['fasttext.FastText._FastText']:
    try:
        model = fasttext.load_model(path)
    except Exception as e:
        log.warning(f'Language identification model unavailable at {path}: {e}')
        return None

    log.info(f'Loaded language identification model from {path}')
    return model


def identify_language(text: str) -> Optional[tuple[str, float]]:
    """Return the most likely language of the text and its confidence, or None if the model is unavailable.

    The language is a two-letter code for Skynet's locales and the model's label (e.g. por_Latn) otherwise.
    """
    model = _load_model(language_id_model_path)
    if model is None:
        return None

    # fastText refuses input containing newlines
    labels, probabilities = model.predict(' '.join(text.split()))
    label = labels[0].removeprefix('__label__')
    code = _ISO_639_3_TO_1.get(label.split('_')[0], label)

    return code, float(probabilities[0])


def language_name(label: str) -> Optional[str]:
    """Return the English name of a well-supported language label, or None for any other language."""
    return _WELL_SUPPORTED_LANGUAGES.get(label)
