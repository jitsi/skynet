from typing import Optional

from skynet.constants import Locale, response_prefix
from skynet.modules.ttt.summaries.prompts.common import get_language_instruction


def get_summary_prompt(transcript_type: str, locale: Optional[Locale] = None) -> str:
    return f"""You are an AI assistant. Summarize the following {transcript_type} transcript into a clear and concise summary.

Instructions:

1. Identify and include the main discussion points, key updates, decisions, and any important issues raised.
2. Exclude small talk, greetings, and off-topic content.
3. Format the output as plain text using short paragraphs separated by a single blank line.
4. Do not use bullet points, numbered lists, bold text, or headings.
5. Keep the summary clear, concise, and easy to read in under 2 minutes.

{get_language_instruction(locale)}

Start your response with "{response_prefix}".
"""


def summary_emails(locale: Optional[Locale] = None) -> str:
    return get_summary_prompt("emails", locale)


def summary_conversation(locale: Optional[Locale] = None) -> str:
    return get_summary_prompt("conversation", locale)


def summary_meeting(locale: Optional[Locale] = None) -> str:
    return get_summary_prompt("meeting", locale)


def summary_text(locale: Optional[Locale] = None) -> str:
    return get_summary_prompt("text or document", locale)
