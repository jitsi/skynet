ifneq (,$(wildcard ./.env))
    include .env
    export
endif

GIT_HASH ?= $(shell git rev-parse --short HEAD)
PLATFORMS ?= linux/amd64
CACHE_DIR ?= /tmp/docker-cache

login:
	${DOCKER_LOGIN_CMD}

build-summaries:
	$(MAKE) login
	docker buildx build \
	--build-arg="BASE_IMAGE_BUILD=nvidia/cuda:12.3.0-devel-ubuntu20.04" \
	--build-arg="BASE_IMAGE_RUN=nvidia/cuda:12.3.0-runtime-ubuntu20.04" \
	--progress plain \
	--push \
	--platform ${PLATFORMS} \
	--cache-from type=local,src=${CACHE_DIR} \
	--cache-to type=local,dest=${CACHE_DIR},mode=max \
	-t ${IMAGE_REGISTRY}/skynet:summaries-${GIT_HASH} .

build-whisper:
	$(MAKE) login
	docker buildx build \
	--build-arg="BASE_IMAGE_BUILD=nvidia/cuda:11.8.0-cudnn8-devel-ubuntu20.04" \
	--build-arg="BASE_IMAGE_RUN=nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu20.04" \
	--progress plain \
	--push \
	--platform ${PLATFORMS} \
	--cache-from type=local,src=${CACHE_DIR} \
	--cache-to type=local,dest=${CACHE_DIR},mode=max \
	-t ${IMAGE_REGISTRY}/skynet:whisper-${GIT_HASH} .\
