from skynet.modules.ttt.assistant.constants import assistant_default_system_message, assistant_limit_data_to_rag


def get_assistant_chat_messages(
    use_rag: bool,
    use_only_rag_data: bool,
    text: str,
    prompt: str,
    system_message: str,
):
    messages = [('system', system_message or assistant_default_system_message)]

    if use_rag:
        if use_only_rag_data:
            messages.append(('system', assistant_limit_data_to_rag))

        messages.append(('system', '{context}'))

    if text:
        messages.append(('human', text))

    if prompt:
        messages.append(('human', prompt))

    return messages
