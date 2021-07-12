FROM ubuntu:18.04 AS base

USER root

# coloring syntax for headers
ENV CYAN='\033[0;36m'
ENV CLEAR='\033[0m'
ENV DEBIAN_FRONTEND='noninteractive'

# setup ubuntu user
ARG UID_='1000'
ARG GID_='1000'
RUN echo "\n${CYAN}SETUP UBUNTU USER${CLEAR}"; \
    addgroup --gid $GID_ ubuntu && \
    adduser \
        --disabled-password \
        --gecos '' \
        --uid $UID_ \
        --gid $GID_ ubuntu
WORKDIR /home/ubuntu

# update ubuntu and install basic dependencies
RUN echo "\n${CYAN}INSTALL GENERIC DEPENDENCIES${CLEAR}"; \
    apt update && \
    apt install -y \
        graphviz \
        python3-dev \
        python3-pydot \
        software-properties-common \
        wget

# install python3.7 and pip
RUN echo "\n${CYAN}SETUP PYTHON3.7${CLEAR}"; \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt update && \
    apt install --fix-missing -y \
        python3.7 && \
    wget https://bootstrap.pypa.io/get-pip.py && \
    python3.7 get-pip.py && \
    rm -rf /home/ubuntu/get-pip.py

# install OpenEXR
ENV CC gcc
ENV CXX g++
ENV LD_LIBRARY_PATH='/usr/include/python3.7m'
RUN echo "\n${CYAN}INSTALL OPENEXR${NO_COLOR}"; \
    apt update && \
    apt install -y \
        build-essential \
        g++ \
        gcc \
        libopenexr-dev \
        openexr \
        zlib1g-dev

# install hidebound
USER ubuntu
ENV REPO='hidebound'
ENV PYTHONPATH "${PYTHONPATH}:/home/ubuntu/$REPO/python"
RUN echo "\n${CYAN}INSTALL HIDEBOUND{CLEAR}"; \
    pip3.7 install hidebound

ENTRYPOINT [\
    "python3.7", \
    "/home/ubuntu/.local/lib/python3.7/site-packages/hidebound/server/app.py" \
]
