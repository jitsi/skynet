#!/bin/sh
cd llama.cpp
make server
cd ..

poetry run python -m uvicorn skynet.main:app --reload
