ifneq (,$(wildcard ./.env))
	include .env
endif

DISABLE_CACHE ?= 0
GIT_HASH ?= $(shell git rev-parse --short HEAD)
PLATFORMS ?= linux/amd64
BUILD_ARGS =

ifeq ($(DISABLE_CACHE), 1)
  BUILD_ARGS := $(BUILD_ARGS) --no-cache
endif

_login:
	${DOCKER_LOGIN_CMD}

build : _login
	docker buildx build \
		--progress plain \
		--push \
		--platform ${PLATFORMS} \
		$(BUILD_ARGS) \
		-t ${IMAGE_REGISTRY}/skynet:summaries-${GIT_HASH} \
		-t ${IMAGE_REGISTRY}/skynet:whisper-${GIT_HASH} \
		-t ${IMAGE_REGISTRY}/skynet:${GIT_HASH} \
		.

build-cpu : _login
	docker buildx build \
		--progress plain \
		--push \
		--platform ${PLATFORMS} \
		$(BUILD_ARGS) \
		--build-arg BASE_IMAGE_BUILD=ubuntu:22.04 \
		--build-arg BASE_IMAGE_RUN=ubuntu:22.04 \
		--build-arg BUILD_WITH_VLLM=0 \
		-t ${IMAGE_REGISTRY}/skynet:${GIT_HASH}-cpu \
		.

local_build:
	docker buildx build \
		--progress plain \
		--load \
		$(BUILD_ARGS) \
		--build-arg BASE_IMAGE_BUILD=ubuntu:22.04 \
		--build-arg BASE_IMAGE_RUN=ubuntu:22.04 \
		--build-arg BUILD_WITH_VLLM=0 \
		-t jitsi/skynet:latest \
		.
