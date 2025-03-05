#!/bin/sh

poetry run black e2e skynet tools
poetry run usort format e2e skynet tools
