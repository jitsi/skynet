# Skynet Summaries Module

Extracts summaries and action items from a given text. The API wraps the wonderful [ggerganov/llama.cpp](https://github.com/ggerganov/llama.cpp). It is split into two sub-modules, `summaries:dispatcher` and `summaries:executor`.

`summaries:dispatcher` will push jobs and retrieve job results from a Redis queue while `summaries:executor` performs the actual inference. They can both be enabled at the same time or deployed separately.

> All requests to this service will require a standard HTTP Authorization header with a Bearer JWT. Check the [**Authorization page**](auth.md) for detailed information on how to generate JWTs or disable authorization.

## Requirements

- Redis
- Poetry

## Flowchart

<img src="flowchart.jpg" alt="Skynet Summaries Module Flowchart">

## Configuration

All of the configuration is done via env vars. Check the [Skynet Environment Variables](env_vars.md) page for a list of values.

## Running

```bash
# Download the preferred GGUF llama model (e.g. https://huggingface.co/TheBloke/Llama-2-7b-Chat-GGUF) and point LLAMA_PATH to it
mkdir skynet/models

wget -q --show-progress "https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf?download=true" -O skynet/models/llama-2-7b-chat.Q4_K_M.gguf

export LLAMA_PATH="$(pwd)/skynet/models/llama-2-7b-chat.Q4_K_M.gguf"

# start Redis
docker run -d --rm -p 6379:6379 redis 

poetry install
./run.sh
```

Visit http://127.0.0.1:8000

## Build Image

```bash
docker buildx build -f summaries.Dockerfile --push --progress plain --platform linux/amd64 -t your-registry/skynet:your-tag .
```

When running the resulting image, make sure to mount a model under `/models` on the container fs.

## Using GPU acceleration on an M1 Mac

Run this before starting Skynet:

```bash
export LLAMA_CPP_LIB=`pwd`/libllama-bin/libllama-m1.so
```

Make sure you use the right file name.

### Code samples

JavaScript: https://github.com/jitsi/skynet/blob/master/docs/sample.js

## Some benchmarks

Summary:

| Model | Input size | Time to summarize (M1 CPU)  | Time to summarize (GPU) |
| :---- | :--------: |:---------------------------:|:-----------------------:|
| [llama-2-7b-chat.Q4_K_M.gguf][1] | 16000 chars |           ~87 sec           |         ~44 sec         |
| [llama-2-7b-chat.Q4_K_M.gguf][1] | 8000 chars |           ~51 sec           |         ~28 sec         |

[1]: https://huggingface.co/TheBloke/Llama-2-7b-Chat-GGUF/blob/main/llama-2-7b-chat.Q4_K_M.gguf
