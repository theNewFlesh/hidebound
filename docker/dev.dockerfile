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
        --gid $GID_ ubuntu && \
    usermod -aG root ubuntu
WORKDIR /home/ubuntu

# update ubuntu and install basic dependencies
RUN echo "\n${CYAN}INSTALL GENERIC DEPENDENCIES${CLEAR}"; \
    apt update && \
    apt install -y \
        curl \
        chromium-chromedriver \
        git \
        graphviz \
        pandoc \
        parallel \
        python3-pydot \
        python3.7-dev \
        software-properties-common \
        tree \
        vim \
        wget

# install zsh
RUN echo "\n${CYAN}SETUP ZSH${CLEAR}"; \
    apt install -y zsh && \
    curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh \
        -o install-oh-my-zsh.sh && \
    echo y | sh install-oh-my-zsh.sh && \
    cp -r /root/.oh-my-zsh /home/ubuntu/ && \
    chown -R ubuntu:ubuntu \
        .oh-my-zsh \
        install-oh-my-zsh.sh && \
    echo 'UTC' > /etc/timezone

# install python3.7 and pip
RUN echo "\n${CYAN}SETUP PYTHON3.7${CLEAR}"; \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt update && \
    apt install --fix-missing -y \
        python3.7 && \
    wget https://bootstrap.pypa.io/get-pip.py && \
    python3.7 get-pip.py && \
    chown -R ubuntu:ubuntu get-pip.py

# install node.js, needed by jupyterlab
RUN echo "\n${CYAN}INSTALL NODE.JS${CLEAR}"; \
    curl -sL https://deb.nodesource.com/setup_16.x | bash - && \
    apt upgrade -y && \
    apt install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

USER ubuntu
ENV PATH="/home/ubuntu/.local/bin:$PATH"
COPY ./henanigans.zsh-theme .oh-my-zsh/custom/themes/henanigans.zsh-theme
COPY ./zshrc .zshrc

ENV LANG "C"
ENV LANGUAGE "C"
ENV LC_ALL "C"
# ------------------------------------------------------------------------------

FROM base AS dev

USER root
WORKDIR /home/ubuntu
ENV REPO='hidebound'
ENV PYTHONPATH "${PYTHONPATH}:/home/ubuntu/$REPO/python"
ENV REPO_ENV=True

# install OpenEXR
ENV CC=gcc
ENV CXX=g++
ENV LD_LIBRARY_PATH='/usr/include/python3.7m/dist-packages'
RUN echo "\n${CYAN}INSTALL OPENEXR${CLEAR}"; \
    apt update && \
    apt install -y \
        build-essential \
        g++ \
        gcc \
        libopenexr-dev \
        openexr \
        python3.7-dev \
        zlib1g-dev

USER ubuntu

# install python dependencies
COPY ./dev_requirements.txt dev_requirements.txt
COPY ./prod_requirements.txt prod_requirements.txt
RUN echo "\n${CYAN}INSTALL PYTHON DEPENDENCIES${CLEAR}"; \
    pip3.7 install -r dev_requirements.txt && \
    pip3.7 install -r prod_requirements.txt && \
    jupyter server extension enable --py --user jupyterlab_git
