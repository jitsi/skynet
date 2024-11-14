# Skynet

Skynet is an API server for AI services wrapping several apps and models.

It is comprised of specialized modules which can be enabled or disabled as needed.

- **Summary and Action Items** with vllm (or llama.cpp)
- **Live Transcriptions** with Faster Whisper via websockets
- 🚧 _More to follow_

## Requirements

- Poetry
- Redis

## Summaries Quickstart

```bash
# if VLLM cannot be used, make sure to have Ollama started. In that case LLAMA_PATH should be the model name, like "llama3.1".
export LLAMA_PATH="$HOME/models/Llama-3.1-8B-Instruct-Q8_0.gguf"

# disable authorization (for testing)
export BYPASS_AUTHORIZATION=1

# start Redis
docker run -d --rm -p 6379:6379 redis 

poetry install
./run.sh

# open http://localhost:8000/summaries/docs in a browser
```

## Live Transcriptions Quickstart

> **Note**: Make sure to have ffmpeg < 7 installed and to update the `DYLD_LIBRARY_PATH` with the path to the ffmpeg 
> libraries, e.g. `export DYLD_LIBRARY_PATH=/Users/MyUser/ffmpeg/6.1.2/lib:$DYLD_LIBRARY_PATH`.

```bash
mkdir -p "$HOME/models/streaming-whisper"
export WHISPER_MODEL_NAME="tiny.en"
export BYPASS_AUTHORIZATION="true"
export ENABLED_MODULES="streaming_whisper"
export WHISPER_MODEL_PATH="$HOME/models/streaming-whisper"

poetry install
./run.sh
```

## Testing docker changes
```bash
docker compose -f compose-dev.yaml up --build
docker cp $HOME/models/Llama-3.1-8B-Instruct-Q8_0.gguf skynet-web-1:/models
docker restart skynet-web-1

# localhost:8000 for Skynet APIs
# localhost:8001/metrics for Prometheus metrics
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
