FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu20.04 AS build

ENV PYTHON_VERSION=3.11 \
    PPA_GPG_KEY=F23C5A6CF475977595C89F51BA6932366A755776 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VENV="/app/.venv" \
    POETRY_NO_INTERACTION=1

ENV PATH "${POETRY_HOME}/bin:$PATH"

RUN mkdir /app
RUN mkdir /app/models
WORKDIR /app

# add ppa repo as we don't want to use the default py version
RUN echo "deb https://ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu focal main" >> /etc/apt/sources.list \
    && echo "deb-src https://ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu focal main" >> /etc/apt/sources.list \
    && apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys $PPA_GPG_KEY

RUN export DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
    python$PYTHON_VERSION \
    gcc \
    python$PYTHON_VERSION-dev \
    python$PYTHON_VERSION-venv \
    python$PYTHON_VERSION-distutils \
    git \
    curl \
    libgomp1 \
    cuda-cupti-11-7 \
    gnupg \
    && rm -rf /var/*/apt

# set the CUDA libs include paths
ENV LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/usr/local/cuda-11.7/targets/x86_64-linux/lib"

RUN ln -s /usr/bin/python${PYTHON_VERSION} /usr/bin/python3 \
    && ln -s /usr/bin/python${PYTHON_VERSION} /usr/bin/python

RUN curl -sSL https://install.python-poetry.org | python3 -

COPY pyproject.toml .
COPY poetry.lock .

RUN python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && poetry install --without dev

ENV PATH="$POETRY_VENV/bin:$PATH"

COPY . .

# main ws server
EXPOSE 8000
# metrics server
EXPOSE 8001
# haproxy agent server
EXPOSE 8002

ENTRYPOINT ["python3", "main.py"]
