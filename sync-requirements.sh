#!/bin/sh

poetry export --without-hashes --format=requirements.txt > requirements.txt
git add requirements.txt

poetry export --with vllm --without-hashes --format=requirements.txt > requirements-vllm.txt
git add requirements-vllm.txt

