from typing import Optional

from skynet.constants import Locale, response_prefix
from skynet.modules.ttt.summaries.prompts.common import get_language_instruction


def get_action_items_prompt(transcript_type: str, locale: Optional[Locale] = None) -> str:
    return f"""You are an AI assistant. Your task is to extract all action items from the following {transcript_type} transcript.

Instructions:

1. Return a list of action items that are either explicitly assigned or clearly implied.
2. Each item should be one line, formatted as: <Task Description> [Owner]
3. If the owner is not explicitly mentioned, omit it — do not guess.
4. Do not repeat or rephrase items multiple times.
5. Format the result as plain text with one action item per line. Do not include explanations, revisions, bullets, or headings.

{get_language_instruction(locale)}

If there are no action items, respond just with "No action items", else start your response with "{response_prefix}", followed by the list of action items.
"""


def action_items_emails(locale: Optional[Locale] = None) -> str:
    return get_action_items_prompt("emails", locale)


def action_items_conversation(locale: Optional[Locale] = None) -> str:
    return get_action_items_prompt("conversation", locale)


def action_items_meeting(locale: Optional[Locale] = None) -> str:
    return get_action_items_prompt("meeting", locale)


def action_items_text(locale: Optional[Locale] = None) -> str:
    return get_action_items_prompt("text or document", locale)
