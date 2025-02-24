#!/bin/sh

cd /app
. .venv/bin/activate
exec python -m skynet.main
