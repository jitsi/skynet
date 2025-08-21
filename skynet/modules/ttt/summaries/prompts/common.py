from skynet.constants import Locale


stick_to_main_language = "Respond using the main language of the provided text."


def set_response_language(locale: Locale) -> str:
    if not locale:
        return stick_to_main_language

    return f'Make sure that you respond in {locale.name.lower()}.'
