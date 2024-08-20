ifneq (,$(wildcard ./.env))
	include .env
endif

GIT_HASH ?= $(shell git rev-parse --short HEAD)
PLATFORMS ?= linux/amd64
CACHE_DIR ?= /tmp/docker-cache

_login:
	${DOCKER_LOGIN_CMD}

build-summaries : _login
	docker buildx build \
	--build-arg="BASE_IMAGE_BUILD=nvidia/cuda:12.2.2-cudnn8-devel-ubuntu22.04" \
	--build-arg="BASE_IMAGE_RUN=nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04" \
	--progress plain \
	--push \
	--platform ${PLATFORMS} \
	-t ${IMAGE_REGISTRY}/skynet:summaries-${GIT_HASH} .

build-whisper : _login
	docker buildx build \
	--build-arg="BASE_IMAGE_BUILD=nvidia/cuda:12.2.2-cudnn8-devel-ubuntu22.04" \
	--build-arg="BASE_IMAGE_RUN=nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04" \
	--progress plain \
	--platform ${PLATFORMS} \
	--push \
	-t ${IMAGE_REGISTRY}/skynet:whisper-${GIT_HASH} .
