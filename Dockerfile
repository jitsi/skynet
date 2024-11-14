ARG BASE_IMAGE_BUILD=nvidia/cuda:12.2.2-cudnn8-devel-ubuntu22.04
ARG BASE_IMAGE_RUN=nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04

## Base Image

FROM ${BASE_IMAGE_BUILD} AS builder

RUN \
    apt-get update && \
    apt-get install -y apt-transport-https ca-certificates gnupg git

COPY docker/rootfs/ /

RUN \
    apt-dpkg-wrap apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys F23C5A6CF475977595C89F51BA6932366A755776 && \
    apt-dpkg-wrap apt-get update && \
    apt-dpkg-wrap apt-get install -y build-essential libcurl4-openssl-dev python3.11 python3.11-venv && \
    apt-cleanup

COPY requirements.txt /app/

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=on

RUN \
    python3.11 -m venv .venv && \
    . .venv/bin/activate && \
    pip install -vvv -r requirements.txt

## Build ffmpeg

FROM ${BASE_IMAGE_RUN} AS ffmpeg_install

COPY docker/rootfs/ /

# ffmpeg build dependencies
RUN \
    apt-dpkg-wrap apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys F23C5A6CF475977595C89F51BA6932366A755776 && \
    apt-dpkg-wrap apt-get update && \
    apt-dpkg-wrap apt-get install -y \
        autoconf \
        automake \
        build-essential \
        cmake \
        libopus-dev \
        libopus0 \
        libtool \
        pkg-config \
        texinfo \
        wget \
        yasm \
        zlib1g \
        zlib1g-dev && \
    apt-cleanup

# Build ffmpeg6 (required for pytorch which only supports ffmpeg < v7)
RUN \
    mkdir -p /opt/ffmpeg && \
    cd /opt/ && \
    wget -q https://www.ffmpeg.org/releases/ffmpeg-6.1.2.tar.gz && \
    tar -xzf ffmpeg-6.1.2.tar.gz -C /opt/ffmpeg --strip-components 1 && \
    rm ffmpeg-6.1.2.tar.gz && \
    cd /opt/ffmpeg/ && \
    ./configure \
      --enable-shared \
      --enable-gpl \
      --enable-libopus && \
    make && \
    make install && \
    ldconfig

RUN \
    apt-dpkg-wrap apt-get autoremove -y \
        autoconf \
        automake \
        build-essential \
        cmake \
        libopus-dev \
        libtool \
        pkg-config \
        texinfo \
        wget \
        yasm \
        zlib1g-dev

## Production Image

FROM ffmpeg_install

RUN \
    apt-get update && \
    apt-get install -y apt-transport-https ca-certificates gnupg

COPY docker/rootfs/ /
COPY --chown=jitsi:jitsi docker/run-skynet.sh /opt/

RUN \
    apt-dpkg-wrap apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys F23C5A6CF475977595C89F51BA6932366A755776 && \
    apt-dpkg-wrap apt-get update && \
    apt-dpkg-wrap apt-get install -y python3.11 python3.11-venv tini libgomp1 strace gdb && \
    apt-cleanup

# Principle of least privilege: create a new user for running the application
RUN \
    groupadd -g 1001 jitsi && \
    useradd -r -u 1001 -g jitsi jitsi

# Copy virtual environment
COPY --chown=jitsi:jitsi --from=builder /app/.venv /app/.venv

# Copy application files
COPY --chown=jitsi:jitsi /skynet /app/skynet/

ENV \
    # https://docs.python.org/3/using/cmdline.html#envvar-PYTHONUNBUFFERED
    PYTHONUNBUFFERED=1 \
    # https://docs.python.org/3/using/cmdline.html#envvar-PYTHONDONTWRITEBYTECODE
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    OUTLINES_CACHE_DIR=/app/vllm/outlines \
    VLLM_CONFIG_ROOT=/app/vllm/config \
    HF_HOME=/app/hf  \
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
