# Skynet

Skynet is an API server for AI services wrapping several APIs and models.

## Running

```bash
poetry install
poetry run uvicorn skynet.main:app
```

Visit
http://127.0.0.1:8000/latest/docs#/
http://127.0.0.1:8000/openai-api/docs#/
