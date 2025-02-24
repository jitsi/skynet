# Skynet RAG Assistant Module

Enable the module by setting the `ENABLED_MODULES` env var to `assistant`.

Allows you to index a crawled website into a vector store, save the store locally and in an s3 bucket and have it augment the prompt with relevant information for various AI assistant tasks.

> All requests to this service will require a standard HTTP Authorization header with a Bearer JWT. Check the [**Authorization page**](auth.md) for detailed information on how to generate JWTs or disable authorization.

## Requirements

- Redis
- Poetry

## Configuration

All of the configuration is done via env vars. Check the [Skynet Environment Variables](env_vars.md) page for a list of values.

## Authorization

Each vector store corresponds to a unique identifier, which the current implementation expects to be provided as a customer id parameter, which can be either be a `cid` field in a JWT, or as a `customer_id` query parameter

Thus, when deploying this module, the deployer will also have the responsibility for establishing the access-control list based on this spec.

## First run

```bash
# start Redis
docker run -d --rm -p 6379:6379 redis

# If using vLLM (running on NVIDIA GPU)
export LLAMA_PATH="$HOME/models/Llama-3.1-8B-Instruct"
poetry install --with vllm

# If using Ollama
export LLAMA_PATH="llama.3.1"
poetry install

./run.sh
```

Visit http://127.0.0.1:8000

## Build Image

```bash
docker buildx build --push --progress plain --platform linux/amd64 -t your-registry/skynet:your-tag .
```

When running the resulting image, make sure to mount a model under `/models` on the container fs.

### Code samples

JavaScript: https://github.com/jitsi/skynet/blob/master/docs/sample.js
