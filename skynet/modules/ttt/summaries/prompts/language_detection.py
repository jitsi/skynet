LANGUAGE_DETECTION_PROMPT = """Detect the primary language of the following text. Respond with ONLY the language code.

Supported languages and their codes:
- English: en
- French: fr
- German: de
- Italian: it
- Spanish: es

If the text is in a different language or you cannot determine the language, respond with: unknown

Text to analyze:
{text}"""
