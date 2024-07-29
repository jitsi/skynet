action_items_conversation_prompt = """
  ## Instructions
    You will be provided a text transcript of a conversation which may or may not contain some action items that need to be taken by the conversation participants.
    An action item is valid when a participant commits to doing something in the future.
    Each action item should be on a separate line.
    If there is at least one action item, start your response with "Action_items:".
    If nobody has any action items, please write "No action items."

    ## Transcript
    {text}

    ## Response
"""

action_items_text_prompt = """
    ## Instructions
    You will be provided a text transcript which may or may not contain some action items that need to be taken by the conversation participants.
    An action item is valid when a participant commits to doing something in the future.
    Each action item should be on a separate line.
    If there is at least one action item, start your response with "Action_items:".
    If nobody has any action items, please write "No action items."

    ## Transcript
    {text}

    ## Response
"""
