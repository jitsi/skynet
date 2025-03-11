ARG BASE_IMAGE_BUILD=nvidia/cuda:12.2.2-cudnn8-devel-ubuntu22.04
ARG BASE_IMAGE_RUN=nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04

## Base Image

FROM ${BASE_IMAGE_BUILD} AS builder
ARG BUILD_WITH_VLLM=1

RUN \
    apt-get update && \
    apt-get install -y apt-transport-https ca-certificates

COPY docker/rootfs/ /

RUN \
    apt-dpkg-wrap apt-get update && \
    apt-dpkg-wrap apt-get install -y build-essential python3.11 python3.11-venv

COPY requirements*.txt /app/
COPY pyproject.toml /app/
COPY skynet /app/skynet

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=on

RUN \
    python3.11 -m venv .venv && \
    . .venv/bin/activate && \
    if [ "$BUILD_WITH_VLLM" = "1" ]; then \
        echo "Building with VLLM"; \
        pip install -r requirements-vllm.txt . ; \
    else \
        echo "Building without VLLM"; \
        pip install -r requirements.txt . ; \
    fi

## Build ffmpeg

FROM builder AS ffmpeg_builder

# ffmpeg build dependencies
RUN \
    apt-dpkg-wrap apt-get install -y \
        autoconf \
        automake \
        libopus-dev \
        libopus0 \
        libtool \
        pkg-config \
        texinfo \
        wget \
        yasm \
        zlib1g \
        zlib1g-dev

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
    JOBS="$(nproc)" && \
    make -j "${JOBS}" && \
    make install && \
    ldconfig

WORKDIR /copy_libs
RUN cp -a /usr/local/lib/lib* ./

## Production Image

FROM ${BASE_IMAGE_RUN}

COPY --chown=jitsi:jitsi docker/run-skynet.sh /opt/
COPY --from=ffmpeg_builder /usr/local/include /usr/local/include
COPY --from=ffmpeg_builder /copy_libs/ /usr/local/lib/
COPY --from=ffmpeg_builder /usr/local/lib/pkgconfig /usr/local/lib/pkgconfig
COPY --chown=jitsi:jitsi --from=builder /app/.venv /app/.venv

RUN \
    apt-get update && \
    apt-get install -y apt-transport-https ca-certificates

COPY docker/rootfs/ /

RUN \
    apt-get update && \
    apt-dpkg-wrap apt-get install -y python3.11 python3.11-venv tini libgomp1 libopus0 zlib1g strace gdb && \
    apt-cleanup

# Principle of least privilege: create a new user for running the application
RUN \
    groupadd -g 1001 jitsi && \
    useradd -r -u 1001 -g jitsi jitsi

ENV \
    # https://docs.python.org/3/using/cmdline.html#envvar-PYTHONUNBUFFERED
    PYTHONUNBUFFERED=1 \
    # https://docs.python.org/3/using/cmdline.html#envvar-PYTHONDONTWRITEBYTECODE
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    OUTLINES_CACHE_DIR=/app/vllm/outlines \
    VLLM_CONFIG_ROOT=/app/vllm/config \
    HF_HOME=/app/hf

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
