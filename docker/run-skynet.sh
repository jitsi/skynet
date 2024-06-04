#!/usr/bin/env bash

cd /app
. .venv/bin/activate

if [[ ${ENABLED_MODULES:="summaries:dispatcher,summaries:executor"} == *"summaries:executor"* ]]; then
  /app/llama.cpp/server \
    -m ${LLAMA_PATH} \
    -b ${LLAMA_N_BATCH:=512} \
    -c ${LLAMA_N_CTX:=8192} \
    -ngl ${LLAMA_N_GPU_LAYERS:=40} \
    --port ${OPENAI_API_SERVER_PORT:=8002} & \
fi

exec python3.11 skynet/main.py

wait -n
