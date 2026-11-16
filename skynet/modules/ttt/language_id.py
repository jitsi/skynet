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
    """Return the most likely language code of the text and its confidence, or None if the model is unavailable."""
    model = _load_model(language_id_model_path)
    if model is None:
        return None

    # fastText refuses input containing newlines
    labels, probabilities = model.predict(' '.join(text.split()))
    code = labels[0].removeprefix('__label__').split('_')[0]

    return _ISO_639_3_TO_1.get(code, code), float(probabilities[0])
