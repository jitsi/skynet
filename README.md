# Skynet

Skynet is an API server for AI services wrapping several APIs and models.

## Usage
All requests to this service will require a standard HTTP Authorization header with a Bearer JWT
You can generate a valid JWT in two ways:

1. Have a JaaS account (https://jaas-pilot.8x8.vc or https://jaas.8x8.vc if using production) and use one of the JaaS public - private key pairs to generate the JWT as specified [here](https://developer.8x8.com/jaas/docs/api-keys-jwt). Currently, the tokens will be considered valid as long as they have the header in the specified format (alg, kid and typ), no validation being done on the body of the token, but this might change in the future.
2. Have a private - public key pair for generating JWTs as specified above, and share the public key with us.

### Code samples

JavaScript: https://github.com/jitsi/skynet/blob/master/docs/sample.js


### [Flowchart](https://github.com/jitsi/skynet/blob/master/docs/flowchart.drawio)

## Running

Download GGUF llama model (e.g. https://huggingface.co/TheBloke/Llama-2-7b-Chat-GGUF) and point LLAMA_PATH to it

```bash
poetry install
poetry run uvicorn skynet.main:app
```

Visit
http://127.0.0.1:8000/latest/docs#/
http://127.0.0.1:8000/openai-api/docs#/

### Using GPU acceleration on an M1 Mac

Run this before starting Skynet:

```bash
export LLAMA_CPP_LIB=`pwd`/libllama-bin/libllama-m1.so
```

Make sure you use the right file name.

## Some benchmarks

Summary:

Model | Input size | Document chunk size | Time to summarize (M1 CPU) | Time to summarize (GPU) |
|---|---|---|---|---|
| [llama-2-7b-chat.Q4_K_M.gguf][1] | 16000 chars | 4000 chars | ~87 sec | ~44 sec |
| [llama-2-7b-chat.Q4_K_M.gguf][1] | 8000 chars | 4000 chars | ~51 sec | ~28 sec  |

[1]: https://huggingface.co/TheBloke/Llama-2-7b-Chat-GGUF/blob/main/llama-2-7b-chat.Q4_K_M.gguf
