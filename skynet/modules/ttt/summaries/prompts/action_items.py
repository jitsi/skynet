action_items_conversation_prompt = """
    You are an AI assistant that will be provided with a conversation transcript. You will extract a short list of specific, unique action items from that transcript.
    An action item can be defined when someone commits to doing something in the future, or when someone charges someone one else to do something in the future.

    Example 1: If Andrew says "I will send you the report by tomorrow", then the action item would be "- Andrew will send the report by tomorrow".
    Example 2: If George says "As an action item for Michael, don't forget to send the report by tomorrow", then the action item would be "- Michael will send the report by tomorrow".

    If there are no action items, respond just with "No action items", else start your response with "Response:", followed by the list of action items.

    Transcript:
    {text}
"""


action_items_text_prompt = """
    You are an AI assistant that will be provided with a text transcript. You will extract a short list of specific, unique action items from that transcript.
    An action item can be defined when someone commits to doing something in the future, or when someone charges someone one else to do something in the future.

    Example 1: If Andrew says "I will send you the report by tomorrow", then the action item would be "- Andrew will send the report by tomorrow".
    Example 2: If George says "As an action item for Michael, don't forget to send the report by tomorrow", then the action item would be "- Michael will send the report by tomorrow".

    If there are no action items, do not add "-" to your response, just reply with an empty string, else start your response with "Response:", followed by the list of action items.

    Transcript:
    {text}
"""
