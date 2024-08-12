action_items_conversation_prompt = """
    You will be provided a conversation transcript which may or may not contain some action items that need to be taken by the conversation participants.
    An action item can be extracted when someone commits to doing something in the future.
    If there are no action items, respond just with "N/A".

    {text}
"""


action_items_text_prompt = """
    You will be provided a text transcript which may or may not contain some action items that need to be taken by the conversation participants.
    An action item can be extracted when someone commits to doing something in the future.
    If there are no action items, respond just with "N/A".

    {text}
"""
