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
# Download the preferred GGUF llama model
mkdir "$HOME/models"

wget -q --show-progress "https://huggingface.co/jitsi/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct-Q4_K_M.gguf?download=true" -O "$HOME/models/llama-3-8b-instruct.Q4_K_M.gguf"

export LLAMA_PATH="$HOME/models/llama-3-8b-instruct.Q4_K_M.gguf"

# start Redis
docker run -d --rm -p 6379:6379 redis 

# disable authorization (for testing)
export BYPASS_AUTHORIZATION=1

poetry install
./run.sh

# open http://localhost:8000/summaries/docs in a browser
```

## Live Transcriptions Quickstart

```bash
mkdir -p "$HOME/models/streaming-whisper"
export WHISPER_MODEL_NAME="tiny.en"
export BYPASS_AUTHORIZATION="true"
export ENABLED_MODULES="streaming_whisper"
export WHISPER_MODEL_PATH="$HOME/models/streaming-whisper"

poetry install
./run.sh
```
### Test it from Github Pages
Go to [Streaming Whisper Demo](https://jitsi.github.io/skynet/) to test your deployment from a browser

OR 

### Run the demo yourself

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
