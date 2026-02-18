from typing import Optional

from skynet.constants import Locale


def get_language_instruction(locale: Optional[Locale]) -> str:
    """Get language instruction for prompts."""
    if locale:
        return f"Generate the response in {locale.name.lower()}."
    return (
        "Identify the predominant language of the transcript (the language used for "
        "the majority of the spoken content, ignoring names, greetings, or occasional "
        "foreign phrases) and generate the response in that language. "
        "If the predominant language is unclear, default to English."
    )
