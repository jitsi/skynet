from skynet.constants import response_prefix


def get_header(transcript_type: str) -> str:
    return f"You are an AI assistant. From a {transcript_type} transcript, extract a **normalized table of contents**."


body = f"""
    Guidelines:
    1. Start from 00:00:00 and normalize all timestamps.
    2. Format each line: `hh:mm:ss – <short, topic-based title>`
    3. **Do not include speaker names** or narrative language.
    4. Avoid vague phrases like "discussion", "talked about", or "shared". Use **topic labels only**.
    5. Eliminate redundant entries — group related content under one heading if needed.
    6. Ensure consistent Markdown formatting and accurate timestamps.

    Example:
    - 00:00:00 – Safari black video issue and KV1 workaround
    - 00:04:00 – Closed captions visibility fix
    - 00:09:12 – Bandwidth estimation improvements and Chrome alignment

    Start your response with "{response_prefix}"
    Now generate the full table of contents:
"""

table_of_contents_emails = f"""
    {get_header("emails")}

    {body}
"""

table_of_contents_conversation = f"""
    {get_header("conversation")}

    {body}
"""

table_of_contents_meeting = f"""
    {get_header("meeting")}

    {body}
"""

table_of_contents_text = f"""
    {get_header("text or document")}

    {body}
"""
