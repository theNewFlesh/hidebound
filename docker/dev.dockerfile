FROM ubuntu:22.04 AS base

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

# setup sudo
RUN echo "\n${CYAN}SETUP SUDO${CLEAR}"; \
    apt update && \
    apt install -y sudo && \
    usermod -aG sudo ubuntu && \
    echo '%ubuntu    ALL = (ALL) NOPASSWD: ALL' >> /etc/sudoers && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /home/ubuntu

# update ubuntu and install basic dependencies
RUN echo "\n${CYAN}INSTALL GENERIC DEPENDENCIES${CLEAR}"; \
    apt update && \
    apt install -y \
        bat \
        curl \
        exa \
        git \
        graphviz \
        npm \
        pandoc \
        parallel \
        ripgrep \
        software-properties-common \
        vim \
        wget && \
    rm -rf /var/lib/apt/lists/*

RUN echo "\n${CYAN}INSTALL PYTHON${CLEAR}"; \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt update && \
    apt install -y \
        python3-pydot \
        python3.10-dev \
        python3.10-venv \
        python3.10-distutils \
        python3.9-dev \
        python3.9-venv \
        python3.9-distutils \
        python3.8-dev \
        python3.8-venv \
        python3.8-distutils \
        python3.7-dev \
        python3.7-venv \
        python3.7-distutils && \
    rm -rf /var/lib/apt/lists/*

RUN echo "\n${CYAN}INSTALL PIP${CLEAR}"; \
    wget https://bootstrap.pypa.io/get-pip.py && \
    python3.10 get-pip.py && \
    pip3.10 install --upgrade pip && \
    rm -rf get-pip.py

# install zsh
RUN echo "\n${CYAN}SETUP ZSH${CLEAR}"; \
    apt update && \
    apt install -y zsh && \
    rm -rf /var/lib/apt/lists/* && \
    curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh \
        -o install-oh-my-zsh.sh && \
    echo y | sh install-oh-my-zsh.sh && \
    mkdir -p /root/.oh-my-zsh/custom/plugins && \
    cd /root/.oh-my-zsh/custom/plugins && \
    git clone https://github.com/zdharma-continuum/fast-syntax-highlighting && \
    git clone https://github.com/zsh-users/zsh-autosuggestions && \
    npm i -g zsh-history-enquirer --unsafe-perm && \
    cd /home/ubuntu && \
    cp -r /root/.oh-my-zsh /home/ubuntu/ && \
    chown -R ubuntu:ubuntu .oh-my-zsh && \
    rm -rf install-oh-my-zsh.sh && \
    echo 'UTC' > /etc/timezone

# install tini
RUN echo "\n${CYAN}INSTALL TINI${CLEAR}"; \
    curl -LJ https://github.com/krallin/tini/releases/download/v0.19.0/tini \
        -o /usr/bin/tini && \
    chown ubuntu:ubuntu /usr/bin/tini && \
    chmod +x /usr/bin/tini

USER ubuntu
ENV PATH="/home/ubuntu/.local/bin:$PATH"
COPY ./config/henanigans.zsh-theme .oh-my-zsh/custom/themes/henanigans.zsh-theme

ENV LANG "C.UTF-8"
ENV LANGUAGE "C.UTF-8"
ENV LC_ALL "C.UTF-8"
# ------------------------------------------------------------------------------

FROM base AS dev

USER root
# chown /var/log
RUN echo "\n${CYAN}CHOWN /VAR/LOG${CLEAR}"; \
    chown ubuntu:ubuntu /var/log

# install chromium
RUN echo "\n${CYAN}INSTALL CHROMIUM${CLEAR}"; \
    apt update && \
    apt install -y chromium-chromedriver && \
    rm -rf /var/lib/apt/lists/*

USER ubuntu
WORKDIR /home/ubuntu

RUN echo "\n${CYAN}INSTALL DEV DEPENDENCIES${CLEAR}"; \
    curl -sSL \
        https://raw.githubusercontent.com/pdm-project/pdm/main/install-pdm.py \
    | python3.10 - && \
    pip3.10 install --upgrade --user \
        pdm \
        'rolling-pin>=0.9.2' && \
    mkdir -p /home/ubuntu/.oh-my-zsh/custom/completions && \
    pdm completion zsh > /home/ubuntu/.oh-my-zsh/custom/completions/_pdm

COPY --chown=ubuntu:ubuntu config/* /home/ubuntu/config/
COPY --chown=ubuntu:ubuntu scripts/* /home/ubuntu/scripts/
RUN echo "\n${CYAN}SETUP DIRECTORIES${CLEAR}"; \
    mkdir pdm

WORKDIR /home/ubuntu/pdm
RUN echo "\n${CYAN}INSTALL DEV ENVIRONMENT${CLEAR}"; \
    . /home/ubuntu/scripts/x_tools.sh && \
    export CONFIG_DIR=/home/ubuntu/config && \
    export SCRIPT_DIR=/home/ubuntu/scripts && \
    x_env_init dev 3.10 && \
    cd /home/ubuntu && \
    ln -s `_x_env_get_path dev 3.10` .dev-env && \
    ln -s `_x_env_get_path dev 3.10`/lib/python3.10/site-packages .dev-packages

RUN echo "\n${CYAN}INSTALL PROD ENVIRONMENTS${CLEAR}"; \
    . /home/ubuntu/scripts/x_tools.sh && \
    export CONFIG_DIR=/home/ubuntu/config && \
    export SCRIPT_DIR=/home/ubuntu/scripts && \
    x_env_init prod 3.10 && \
    x_env_init prod 3.9 && \
    x_env_init prod 3.8 && \
    x_env_init prod 3.7

WORKDIR /home/ubuntu
RUN echo "\n${CYAN}REMOVE DIRECTORIES${CLEAR}"; \
    rm -rf config scripts

ENV REPO='hidebound'
ENV PYTHONPATH ":/home/ubuntu/$REPO/python:/home/ubuntu/.local/lib"
ENV PYTHONPYCACHEPREFIX "/home/ubuntu/.python_cache"

ENTRYPOINT ["/usr/bin/tini", "--"]