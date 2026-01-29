from typing import Optional

from skynet.constants import Locale, response_prefix
from skynet.modules.ttt.summaries.prompts.common import get_language_instruction


def get_table_of_contents_prompt(transcript_type: str, locale: Optional[Locale] = None) -> str:
    return f"""You are an AI assistant. From a {transcript_type} transcript, extract a normalized table of contents.

Guidelines:

1. Start from 00:00:00 and normalize all timestamps.
2. Format each line: hh:mm:ss – <short, topic-based title>
3. Do not include speaker names or narrative language.
4. Avoid vague phrases like "discussion", "talked about", or "shared". Use topic labels only.
5. Eliminate redundant entries — group related content under one heading if needed.
6. Ensure consistent formatting and accurate timestamps.

Example:
- 00:00:00 – Safari black video issue and KV1 workaround
- 00:04:00 – Closed captions visibility fix
- 00:09:12 – Bandwidth estimation improvements and Chrome alignment

{get_language_instruction(locale)}

Start your response with "{response_prefix}".
"""


def table_of_contents_emails(locale: Optional[Locale] = None) -> str:
    return get_table_of_contents_prompt("emails", locale)


def table_of_contents_conversation(locale: Optional[Locale] = None) -> str:
    return get_table_of_contents_prompt("conversation", locale)


def table_of_contents_meeting(locale: Optional[Locale] = None) -> str:
    return get_table_of_contents_prompt("meeting", locale)


def table_of_contents_text(locale: Optional[Locale] = None) -> str:
    return get_table_of_contents_prompt("text or document", locale)
