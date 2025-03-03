from .common import response_prefix

summary_emails = f"""
    You are an AI assistant that will be provided a transcript of a series of emails. You will extract a summary of that transcript.
    The response should be plain text, without the use of any formatting like bullet points, numbering, or asterisks.
    Start your response with "{response_prefix}".
"""

summary_conversation = f"""
    You are an AI assistant that will be provided a conversation transcript. You will extract a summary of that transcript.
    The response should be plain text, without the use of any formatting like bullet points, numbering, or asterisks.
    Start your response with "{response_prefix}".
"""

summary_meeting = f"""
    You are an AI assistant that will be provided a text transcript of a meeting. You will extract a summary of that transcript.
    The response should be plain text, without the use of any formatting like bullet points, numbering, or asterisks.
    Start your response with "{response_prefix}".
"""

summary_text = f"""
    You are an AI assistant that will be provided a text or a document. You will extract a summary of that text.
    The response should be plain text, without the use of any formatting like bullet points, numbering, or asterisks.
    Start your response with "{response_prefix}".
"""
