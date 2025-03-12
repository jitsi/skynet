from skynet.constants import Locale


stick_to_main_language = "Respond using the main language of the provided text."
response_prefix = "SkynetResponse"


def set_response_language(locale: Locale) -> str:
    if not locale:
        return stick_to_main_language

    return f'Respond in {locale.name.lower()}.'
