#!/bin/sh

if nvcc --version
then
  export CUDA_VISIBLE_DEVICES=0
  export LLAMA_N_CTX=90000
else
  export LLAMA_N_CTX=8192
fi

poetry run python -m skynet.main
