#!/bin/sh

poetry run autoflake --recursive --remove-all-unused-imports --remove-unused-variables --in-place e2e skynet tools
poetry run black e2e skynet tools
poetry run usort format e2e skynet tools
