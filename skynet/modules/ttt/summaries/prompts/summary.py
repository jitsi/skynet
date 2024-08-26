summary_conversation_prompt = """
    You are an AI assistant that will be provided a conversation transcript. You will extract a summary of that transcript.
    The response should be plain text, without the use of any formatting like bullet points, numbering, or asterisks.
    Start your response with "Response:".

    Text:
    {text}
"""

summary_text_prompt = """
    You are an AI assistant that will be provided a text transcript. You will extract a summary of that transcript.
    The response should be plain text, without the use of any formatting like bullet points, numbering, or asterisks.
    Start your response with "Response:".

    Text:
    {text}
"""
