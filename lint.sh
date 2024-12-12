#!/bin/sh

poetry run black skynet tools
poetry run usort format skynet tools
