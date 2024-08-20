ARG BASE_IMAGE_BUILD=nvidia/cuda:12.2.2-cudnn8-devel-ubuntu22.04
ARG BASE_IMAGE_RUN=nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04

## Base Image
##

FROM ${BASE_IMAGE_BUILD} AS builder

RUN \
    apt-get update && \
    apt-get install -y apt-transport-https ca-certificates gnupg git

COPY docker/rootfs/ /

RUN \
    apt-dpkg-wrap apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys F23C5A6CF475977595C89F51BA6932366A755776 && \
    apt-dpkg-wrap apt-get update && \
    apt-dpkg-wrap apt-get install -y wget build-essential libcurl4-openssl-dev python3.11 python3.11-venv

RUN \
    wget -nv -O cmake.sh https://github.com/Kitware/CMake/releases/download/v3.29.3/cmake-3.29.3-linux-x86_64.sh && \
    sh cmake.sh --skip-license --prefix=/usr/local && \
    rm cmake.sh

COPY llama.cpp llama.cpp
RUN \
    cd llama.cpp && \
    rm -rf build && \
    cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DGGML_NATIVE=OFF -DBUILD_SHARED_LIBS=OFF && \
    cmake --build build --target llama-server -j`getconf _NPROCESSORS_ONLN` && \
    ldd build/bin/llama-server

COPY requirements.txt /app/

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=on

RUN \
    python3.11 -m venv .venv && \
    . .venv/bin/activate && \
    pip install -vvv -r requirements.txt

## Production Image
##

FROM ${BASE_IMAGE_RUN}

RUN \
    apt-get update && \
    apt-get install -y apt-transport-https ca-certificates gnupg

COPY docker/rootfs/ /
COPY --chown=jitsi:jitsi docker/run-skynet.sh /opt/

RUN \
    apt-dpkg-wrap apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys F23C5A6CF475977595C89F51BA6932366A755776 && \
    apt-dpkg-wrap apt-get update && \
    apt-dpkg-wrap apt-get install -y python3.11 python3.11-venv tini libgomp1 && \
    apt-cleanup

# Principle of least privilege: create a new user for running the application
RUN \
    groupadd -g 1001 jitsi && \
    useradd -r -u 1001 -g jitsi jitsi

# Copy virtual environment
COPY --chown=jitsi:jitsi --from=builder /app/.venv /app/.venv
COPY --chown=jitsi:jitsi --from=builder /llama.cpp/build/bin /app/llama.cpp

RUN ldd /app/llama.cpp/llama-server

# Copy application files
COPY --chown=jitsi:jitsi /skynet /app/skynet/

ENV \
    # https://docs.python.org/3/using/cmdline.html#envvar-PYTHONUNBUFFERED
    PYTHONUNBUFFERED=1 \
    # https://docs.python.org/3/using/cmdline.html#envvar-PYTHONDONTWRITEBYTECODE
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    LLAMA_PATH="/models/Llama-3.1-8B-Instruct-Q8_0.gguf"

VOLUME [ "/models" ]

WORKDIR ${PYTHONPATH}
RUN chown jitsi:jitsi ${PYTHONPATH}

# Document the exposed port
EXPOSE 8000

# Use the unprivileged user to run the application
USER 1001

# Use tini as our PID 1
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run Skynet
CMD ["/opt/run-skynet.sh"]
