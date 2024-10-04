#!/bin/sh

if nvcc --version
then
  export CUDA_VISIBLE_DEVICES=0
else
  cd llama.cpp
  make llama-server
  cd ..
fi

export LLAMA_N_CTX=8192
poetry run python -m uvicorn skynet.main:app --reload
