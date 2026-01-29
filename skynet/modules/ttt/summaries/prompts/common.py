from typing import Optional

from skynet.constants import Locale


stick_to_main_language = "Respond using the main language of the provided text."


def set_response_language(locale: Locale) -> str:
    if not locale:
        return stick_to_main_language

    return f'Make sure that you respond in {locale.name.lower()}.'


def get_language_instruction(locale: Optional[Locale]) -> str:
    """Get language instruction for prompts."""
    if locale:
        return f"Generate the response in {locale.name.lower()}."
    return "Detect the main language of the provided transcript and generate the response in that language."
