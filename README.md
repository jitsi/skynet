# Skynet

Skynet is an API server for AI services wrapping several apps and models.

It is comprised of specialized modules which can be enabled or disabled as needed.

- **Summary and Action Items** with llama.cpp (enabled by default)
- **Live Transcriptions** with Faster Whisper via websockets
- 🚧 _More to follow_

## Requirements

- Poetry
- Redis

## Summaries Quickstart

```bash
# Download the preferred GGUF llama model (e.g. https://huggingface.co/TheBloke/Llama-2-7b-Chat-GGUF) and point LLAMA_PATH to it
mkdir "$HOME/models"

wget -q --show-progress "https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf?download=true" -O "$HOME/models/llama-2-7b-chat.Q4_K_M.gguf"

export LLAMA_PATH="$HOME/models/llama-2-7b-chat.Q4_K_M.gguf"

# start Redis
docker run -d --rm -p 6379:6379 redis 

# disable authorization
export BYPASS_AUTHORIZATION="true"

poetry install
poetry run python skynet/main.py

# open http://localhost:8000/summaries/docs in a browser
```

## Live Transcriptions Quickstart

```bash
mkdir -p "$HOME/my-models-folder/streaming-whisper"
export WHISPER_MODEL_NAME="tiny.en"
export BYPASS_AUTHORIZATION="true"
export ENABLED_MODULES="streaming_whisper"
export WHISPER_MODEL_PATH="$HOME/my-models-folder/streaming-whisper"

poetry install
./run.sh
```

Go to [demos/streaming-whisper/](demos/streaming-whisper/) and start a Python http server.

```bash
python3 -m http.server 8080
```

Open http://127.0.0.1:8080.

## Documentation

Detailed documentation on how to configure, run, build and monitor Skynet and can be found in the [docs](docs/README.md).

## Development

If you want to contribute, make sure to install the pre-commit hook for linting.

```bash
poetry run githooks setup
```

## License

Skynet is distributed under the Apache 2.0 License.
