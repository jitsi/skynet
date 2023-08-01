# Skynet

Skynet is an API server for AI services wrapping several APIs and models.

## Running

Download ggml llama model (e.g. https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGML) and point LLAMA_PATH to it

```bash
poetry install
poetry run uvicorn skynet.main:app
```

Visit
http://127.0.0.1:8000/latest/docs#/
http://127.0.0.1:8000/openai-api/docs#/
