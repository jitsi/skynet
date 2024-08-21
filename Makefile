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
	-t ${IMAGE_REGISTRY}/skynet:latest .
