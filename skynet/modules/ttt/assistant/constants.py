from skynet.constants import response_prefix

assistant_default_system_message = "You are an AI assistant who provides a concise next answer in a given conversation."
assistant_rag_question_extractor = f"""
    Based on the text above, respond just with a concise emerging question usable for similarity search.
    Start your response with "{response_prefix}".
"""
assistant_limit_data_to_rag = "Only respond based on the information provided in the documents above."
