#!/bin/sh

exec poetry run uvicorn skynet.main:app

