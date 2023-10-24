## Model download
##

FROM python:3.11-slim AS model_download

RUN pip install --upgrade huggingface_hub

RUN mkdir /models
WORKDIR /models
COPY download_model.py ./download_model.py
RUN python3 download_model.py

## Base Image
##

FROM nvidia/cuda:12.2.0-runtime-ubuntu20.04 AS base
ARG POETRY_VERSION=1.5.1

# Adapted from https://github.com/max-pfeiffer/python-poetry/blob/main/build/Dockerfile
# and https://github.com/max-pfeiffer/uvicorn-poetry/blob/main/examples/fast_api_multistage_build/Dockerfile

# References:
# https://pip.pypa.io/en/stable/topics/caching/#avoiding-caching
# https://pip.pypa.io/en/stable/cli/pip/?highlight=PIP_NO_CACHE_DIR#cmdoption-no-cache-dir
# https://pip.pypa.io/en/stable/cli/pip/?highlight=PIP_DISABLE_PIP_VERSION_CHECK#cmdoption-disable-pip-version-check
# https://pip.pypa.io/en/stable/cli/pip/?highlight=PIP_DEFAULT_TIMEOUT#cmdoption-timeout
# https://pip.pypa.io/en/stable/topics/configuration/#environment-variables
# https://python-poetry.org/docs/#installation
# https://refspecs.linuxfoundation.org/FHS_2.3/fhs-2.3.html#OPTADDONAPPLICATIONSOFTWAREPACKAGES

ENV DEBIAN_FRONTEND=noninteractive \
    PPA_GPG_KEY=F23C5A6CF475977595C89F51BA6932366A755776 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=${POETRY_VERSION} \
    PYTHON_VERSION=3.11 \
    POETRY_HOME="/opt/poetry"

ENV PATH="$POETRY_HOME/bin:$PATH"

# add ppa repo as we don't want to use the default py version
RUN echo "deb https://ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu focal main" >> /etc/apt/sources.list \
    && echo "deb-src https://ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu focal main" >> /etc/apt/sources.list \
    && apt-key adv --keyserver keyserver.ubuntu.com --recv-keys $PPA_GPG_KEY

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        python$PYTHON_VERSION \
        python3-pip

# https://python-poetry.org/docs/#osx--linux--bashonwindows-install-instructions
RUN apt-get install --no-install-recommends -y \
        build-essential \
        g++ \
        curl \
        tini \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && apt-get purge --auto-remove -y \
      build-essential \
      curl

    # https://docs.python.org/3/using/cmdline.html#envvar-PYTHONUNBUFFERED
ENV PYTHONUNBUFFERED=1 \
    # https://docs.python.org/3/using/cmdline.html#envvar-PYTHONDONTWRITEBYTECODE
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    # https://python-poetry.org/docs/configuration/#virtualenvsin-project
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_CACHE_DIR="/app/.cache" \
    VIRTUAL_ENVIRONMENT_PATH="/app/.venv"

# Adding the virtual environment to PATH in order to "activate" it.
# https://docs.python.org/3/library/venv.html#how-venvs-work
ENV PATH="$VIRTUAL_ENVIRONMENT_PATH/bin:$PATH"

# Principle of least privilege: create a new user for running the application
RUN groupadd -g 1001 jitsi && \
    useradd -r -u 1001 -g jitsi jitsi

# Set the WORKDIR to the application root.
# https://www.uvicorn.org/settings/#development
# https://docs.docker.com/engine/reference/builder/#workdir
WORKDIR ${PYTHONPATH}
RUN chown jitsi:jitsi ${PYTHONPATH}

# Create cache directory and set permissions because user 1001 has no home
# and poetry cache directory.
# https://python-poetry.org/docs/configuration/#cache-directory
RUN mkdir ${POETRY_CACHE_DIR} && chown jitsi:jitsi ${POETRY_CACHE_DIR}

RUN mkdir /models && chown -R 1001:1001 /models
RUN mkdir /libllama && chown -R 1001:1001 /libllama

# Copy libllama
COPY --chown=1001:1001 /libllama-bin/libllama-t4-06abf8e.so /libllama/libllama.so
# Copy models
COPY --chown=jitsi:jitsi --from=model_download /models/* /models/

# Document the exposed port
EXPOSE 3000

# Use the unpriveledged user to run the application
USER 1001

# Use tini as our PID 1
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run the uvicorn application server.
CMD exec poetry run python skynet/main.py

## Builder Image
##

FROM base AS builder

# install [tool.poetry.dependencies]
# this will install virtual environment into /.venv because of POETRY_VIRTUALENVS_IN_PROJECT=true
# see: https://python-poetry.org/docs/configuration/#virtualenvsin-project
COPY ./poetry.lock ./pyproject.toml /app/

ENV CMAKE_ARGS="-DLLAMA_CUBLAS=on"
ENV FORCE_CMAKE=1

RUN LLAMA_CUBLAS=1 poetry install --no-interaction --no-root --without dev

## Production Image
##

FROM base

ENV LLAMA_PATH="/models/llama-2-7b-chat.Q4_K_M.gguf"
ENV LLAMA_CPP_LIB="/libllama/libllama.so"

# Copy virtual environment
COPY --chown=jitsi:jitsi --from=builder /app/.venv /app/.venv

# Copy application files
COPY --chown=jitsi:jitsi /skynet /app/skynet/
