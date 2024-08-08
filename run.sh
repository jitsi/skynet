#!/bin/sh
cd llama.cpp
make llama-server
cd ..

export LLAMA_N_CTX=32000
poetry run python -m uvicorn skynet.main:app --reload
