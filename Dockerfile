ARG BASE_IMAGE_BUILD=nvidia/cuda:12.3.0-devel-ubuntu20.04
ARG BASE_IMAGE_RUN=nvidia/cuda:12.3.0-runtime-ubuntu20.04

## Base Image
##

FROM ${BASE_IMAGE_BUILD} AS builder

RUN \
    apt-get update && \
    apt-get install -y apt-transport-https ca-certificates gnupg git

COPY docker/rootfs/ /

RUN \
    apt-dpkg-wrap apt-key adv --keyserver keyserver.ubuntu.com --recv-keys F23C5A6CF475977595C89F51BA6932366A755776 && \
    apt-dpkg-wrap apt-get update && \
    apt-dpkg-wrap apt-get install -y build-essential python3.11 python3.11-venv libgomp1 cuda-cupti-11-7 && \
    apt-cleanup

COPY requirements.txt /app/
WORKDIR /app

ENV \
    CMAKE_ARGS="-DLLAMA_CUBLAS=ON -DLLAMA_NATIVE=OFF" \
    FORCE_CMAKE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

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
    apt-dpkg-wrap apt-key adv --keyserver keyserver.ubuntu.com --recv-keys F23C5A6CF475977595C89F51BA6932366A755776 && \
    apt-dpkg-wrap apt-get update && \
    apt-dpkg-wrap apt-get install -y python3.11 python3.11-venv tini && \
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
    LLAMA_PATH="/models/llama-2-7b-chat.Q4_K_M.gguf" \
    LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/usr/local/cuda-11.7/targets/x86_64-linux/lib"

VOLUME [ "/models" ]

WORKDIR ${PYTHONPATH}
RUN chown jitsi:jitsi ${PYTHONPATH}

# Document the exposed port
EXPOSE 8000

# Use the unpriviledged user to run the application
USER 1001

# Use tini as our PID 1
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run Skynet
CMD ["/opt/run-skynet.sh"]
