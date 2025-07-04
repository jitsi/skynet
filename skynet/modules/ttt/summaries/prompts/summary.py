from skynet.constants import response_prefix


def get_header(transcript_type: str) -> str:
    return f"You are an AI assistant. Summarize the following {transcript_type} transcript into a clear and concise summary."


body = f"""
    Instructions:

    1. Identify and include the main discussion points, key updates, decisions, and any important issues raised.
    2. Exclude small talk, greetings, and off-topic content.
    3. Format the output as plain text using short paragraphs separated by a single blank line.
    4. Do not use bullet points, numbered lists, bold text, or headings.
    5. Keep the summary clear, concise, and easy to read in under 2 minutes.

    Now generate the summary based on this transcript:

    Start your response with "{response_prefix}".
    Now generate the summary based on this transcript:
"""


summary_emails = f"""
    {get_header("emails")}

    {body}
"""

summary_conversation = f"""
    {get_header("conversation")}

    {body}
"""

summary_meeting = f"""
    {get_header("meeting")}

    {body}
"""

summary_text = f"""
    {get_header("text or document")}

    {body}
"""
