ifneq (,$(wildcard ./.env))
	include .env
endif

GIT_HASH ?= $(shell git rev-parse --short HEAD)
PLATFORMS ?= linux/amd64

_login:
	${DOCKER_LOGIN_CMD}

build : _login
	docker buildx build \
		--progress plain \
		--push \
		--platform ${PLATFORMS} \
		-t ${IMAGE_REGISTRY}/skynet:summaries-${GIT_HASH} \
		-t ${IMAGE_REGISTRY}/skynet:whisper-${GIT_HASH} \
		-t ${IMAGE_REGISTRY}/skynet:${GIT_HASH} \
		.

build-cpu : _login
	docker buildx build \
		--progress plain \
		--push \
		--platform ${PLATFORMS} \
		--build-arg BASE_IMAGE_BUILD=ubuntu:22.04 \
		--build-arg BASE_IMAGE_RUN=ubuntu:22.04 \
		--build-arg BUILD_WITH_VLLM=0 \
		-t ${IMAGE_REGISTRY}/skynet:${GIT_HASH}-cpu \
		.

local_build:
	docker buildx build \
		--progress plain \
		--load \
		--build-arg BASE_IMAGE_BUILD=ubuntu:22.04 \
		--build-arg BASE_IMAGE_RUN=ubuntu:22.04 \
		--build-arg BUILD_WITH_VLLM=0 \
		-t jitsi/skynet:latest \
		.
