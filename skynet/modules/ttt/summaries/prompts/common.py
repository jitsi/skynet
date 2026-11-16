from typing import Optional

from skynet.constants import Locale


def get_language_instruction(language: Optional[Locale | str]) -> str:
    """Get language instruction for prompts, from a Locale or the English name of a detected language."""
    if isinstance(language, Locale):
        language = language.name.lower()

    if language:
        return f"Generate the response in {language}."
    return (
        "Identify the predominant language of the transcript (the language used for "
        "the majority of the spoken content, ignoring names, greetings, or occasional "
        "foreign phrases) and generate the response in that language. "
        "If the predominant language is unclear, default to English."
    )
