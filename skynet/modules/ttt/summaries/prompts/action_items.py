from skynet.constants import response_prefix

body = f"""
    Instructions:

    You are an AI assistant. From the following meeting transcript, extract only the action items.

    Instructions:

    1. Return a list of action items that are either explicitly assigned or clearly implied.
    2. Each item should be one line, formatted as:
    <Task Description> [Owner]
    3. If the owner is not explicitly mentioned, omit it — do not guess.
    4. Do not repeat or rephrase items multiple times.
    5. Format the result as plain text with one action item per line. Do not include explanations, revisions, bullets, or headings.

    If there are no action items, respond just with "No action items", else start your response with "{response_prefix}", followed by the list of action items.
    Now extract all action items from this transcript:
"""


def get_header(transcript_type: str) -> str:
    return f"You are an AI assistant. Your task is to extract all action items from the following {transcript_type} transcript."


action_items_emails = f"""
    {get_header("emails")}

    {body}
"""

action_items_conversation = f"""
    {get_header("conversation")}

    {body}
"""

action_items_meeting = f"""
    {get_header("meeting")}

    {body}
"""

action_items_text = f"""
    {get_header("text or document")}

    {body}
"""
