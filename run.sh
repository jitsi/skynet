#!/usr/bin/env bash

cd llama.cpp
make server
cd ..

DEFAULT_GPU_LAYERS=40

if [ "$(uname)" == "Darwin" ]; then
  DEFAULT_GPU_LAYERS=-1
fi

if [[ ${ENABLED_MODULES:="summaries:dispatcher,summaries:executor"} == *"summaries:executor"* ]]; then
  ${OPENAI_API_SERVER_PATH} \
    -m ${LLAMA_PATH} \
    -b ${LLAMA_N_BATCH:=512} \
    -c ${LLAMA_N_CTX:=8192} \
    -ngl ${LLAMA_N_GPU_LAYERS:=${DEFAULT_GPU_LAYERS}} \
    --port ${OPENAI_API_SERVER_PORT:=8002} & \
fi

poetry run python -m uvicorn skynet.main:app --reload

wait -n
