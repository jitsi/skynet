#!/bin/sh

cd /app
. .venv/bin/activate
exec python3.11 skynet/main.py
