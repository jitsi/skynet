summary_conversation_prompt = """
    ## Instructions
    Provide a summary of the given conversation, following the instructions
    The summary should be just plain text.
    The only formatting allowed is adding a new line between main ideas.
    Do not add any other formatting, such as bullet points, numbering, or asterisks.
    Start your response with "Summary:".

    ## Transcript
    {text}

    ## Response
"""

summary_text_prompt = """
    ## Instructions
    Provide a summary of the given transcript, following the instructions
    The summary should be just plain text.
    The only formatting allowed is adding a new line between main ideas.
    Do not add any other formatting, such as bullet points, numbering, or asterisks.
    Start your response with "Summary:".

    ## Transcript
    {text}

    ## Response
"""
