#!/bin/sh

poetry export --without-hashes --format=requirements.txt > requirements.txt
git add requirements.txt
