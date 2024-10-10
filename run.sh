#!/bin/sh

if nvcc --version
then
  export CUDA_VISIBLE_DEVICES=0
fi

export LLAMA_N_CTX=44000
poetry run python -m uvicorn skynet.main:app --reload
