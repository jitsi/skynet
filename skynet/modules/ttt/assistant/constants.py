from skynet.constants import response_prefix

assistant_default_system_message = "You are an AI assistant who provides the next answer in a given conversation."
assistant_rag_question_extractor = f"""
    Based on the provided text, formulate a proper question for RAG.
    Start your response with "{response_prefix}".
"""
assistant_limit_data_to_rag = "Only respond based on the information provided below."
