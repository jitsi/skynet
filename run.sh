#!/bin/sh

if nvcc --version
then
  export CUDA_VISIBLE_DEVICES=0
fi

export LLAMA_N_CTX=80000

poetry run python -m skynet.main
