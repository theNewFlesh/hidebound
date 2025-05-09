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
        apt-transport-https \
        bat \
        btop \
        ca-certificates \
        cargo \
        curl \
        exa \
        git \
        gnupg \
        graphviz \
        jq \
        parallel \
        ripgrep \
        software-properties-common \
        unzip \
        vim \
        wget && \
    rm -rf /var/lib/apt/lists/*

# install yq
RUN echo "\n${CYAN}INSTALL YQ${CLEAR}"; \
    curl -fsSL \
        https://github.com/mikefarah/yq/releases/download/v4.9.1/yq_linux_amd64 \
        -o /usr/local/bin/yq && \
    chmod +x /usr/local/bin/yq

# install all python versions
RUN echo "\n${CYAN}INSTALL PYTHON${CLEAR}"; \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt update && \
    apt install -y \
        python3-pydot \
        python3.10-dev \
        python3.10-venv \
        python3.9-dev \
        python3.9-venv \
        python3.10-distutils \
        python3.9-distutils \
    && rm -rf /var/lib/apt/lists/*

# install pip
RUN echo "\n${CYAN}INSTALL PIP${CLEAR}"; \
    wget https://bootstrap.pypa.io/get-pip.py && \
    python3.10 get-pip.py && \
    pip3.10 install --upgrade pip && \
    rm -rf get-pip.py

# install nodejs (needed by jupyter lab)
RUN echo "\n${CYAN}INSTALL NODEJS${CLEAR}"; \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
        | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    export NODE_VERSION=20 && \
    echo "deb \
        [signed-by=/etc/apt/keyrings/nodesource.gpg] \
        https://deb.nodesource.com/node_$NODE_VERSION.x \
        nodistro main" \
        | tee /etc/apt/sources.list.d/nodesource.list && \
    apt update && \
    apt install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# install and setup zsh
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

# install s6-overlay
RUN echo "\n${CYAN}INSTALL S6${CLEAR}"; \
    export S6_ARCH="x86_64" && \
    export S6_VERSION="v3.1.5.0" && \
    export S6_URL="https://github.com/just-containers/s6-overlay/releases/download" && \
    curl -fsSL "${S6_URL}/${S6_VERSION}/s6-overlay-noarch.tar.xz" \
        -o /tmp/s6-overlay-noarch.tar.xz && \
    curl -fsSL "${S6_URL}/${S6_VERSION}/s6-overlay-noarch.tar.xz.sha256" \
        -o /tmp/s6-overlay-noarch.tar.xz.sha256 && \
    curl -fsSL "${S6_URL}/${S6_VERSION}/s6-overlay-${S6_ARCH}.tar.xz" \
        -o /tmp/s6-overlay-${S6_ARCH}.tar.xz && \
    curl -fsSL "${S6_URL}/${S6_VERSION}/s6-overlay-${S6_ARCH}.tar.xz.sha256" \
        -o /tmp/s6-overlay-${S6_ARCH}.tar.xz.sha256 && \
    tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz && \
    tar -C / -Jxpf /tmp/s6-overlay-${S6_ARCH}.tar.xz && \
    rm /tmp/s6-overlay-noarch.tar.xz \
       /tmp/s6-overlay-noarch.tar.xz.sha256 \
       /tmp/s6-overlay-${S6_ARCH}.tar.xz \
       /tmp/s6-overlay-${S6_ARCH}.tar.xz.sha256

# install helm
RUN echo "\n${CYAN}INSTALL HELM${CLEAR}"; \
    mkdir -p /tmp/helm && \
    cd /tmp/helm && \
    curl https://get.helm.sh/helm-v3.8.1-linux-amd64.tar.gz -Lo helm.tar.gz && \
    tar zxvf helm.tar.gz && \
    mv linux-amd64/helm /usr/local/bin/ && \
    chmod +x /usr/local/bin/helm && \
    rm -rf /tmp/helm

USER ubuntu
ENV PATH="/home/ubuntu/.local/bin:$PATH"
COPY ./config/henanigans.zsh-theme .oh-my-zsh/custom/themes/henanigans.zsh-theme

ENV LANG "C.UTF-8"
ENV LANGUAGE "C.UTF-8"
ENV LC_ALL "C.UTF-8"
# ------------------------------------------------------------------------------

FROM base AS dev
USER root

# install chromedriver
ENV PATH=$PATH:/lib/chromedriver
RUN echo "\n${CYAN}INSTALL CHROMEDRIVER${CLEAR}"; \
    apt update && \
    apt install -y chromium-chromedriver && \
    rm -rf /var/lib/apt/lists/*

USER ubuntu
WORKDIR /home/ubuntu

# install dev dependencies
RUN echo "\n${CYAN}INSTALL DEV DEPENDENCIES${CLEAR}"; \
    curl -sSL \
        https://raw.githubusercontent.com/pdm-project/pdm/main/install-pdm.py \
        | python3.10 - && \
    pip3.10 install --upgrade --user \
        'pdm>=2.19.1' \
        'pdm-bump<0.7.0' \
        'rolling-pin>=0.11.1' \
        'uv' && \
    mkdir -p /home/ubuntu/.oh-my-zsh/custom/completions && \
    pdm self update --pip-args='--user' && \
    pdm completion zsh > /home/ubuntu/.oh-my-zsh/custom/completions/_pdm

# setup pdm
COPY --chown=ubuntu:ubuntu config/build.yaml /home/ubuntu/config/
COPY --chown=ubuntu:ubuntu config/dev.lock /home/ubuntu/config/
COPY --chown=ubuntu:ubuntu config/pdm.toml /home/ubuntu/config/
COPY --chown=ubuntu:ubuntu config/prod.lock /home/ubuntu/config/
COPY --chown=ubuntu:ubuntu config/pyproject.toml /home/ubuntu/config/
COPY --chown=ubuntu:ubuntu scripts/prod-cli /home/ubuntu/scripts/
COPY --chown=ubuntu:ubuntu scripts/x_tools.sh /home/ubuntu/scripts/
RUN echo "\n${CYAN}SETUP DIRECTORIES${CLEAR}"; \
    mkdir pdm

# create dev env
WORKDIR /home/ubuntu/pdm
RUN echo "\n${CYAN}INSTALL DEV ENVIRONMENT${CLEAR}"; \
    . /home/ubuntu/scripts/x_tools.sh && \
    export CONFIG_DIR=/home/ubuntu/config && \
    export SCRIPT_DIR=/home/ubuntu/scripts && \
    x_env_init dev 3.10 && \
    cd /home/ubuntu && \
    ln -s `_x_env_get_path dev 3.10` .dev-env && \
    ln -s `_x_env_get_path dev 3.10`/lib/python3.10/site-packages .dev-packages

# create prod envs
RUN echo "\n${CYAN}INSTALL PROD ENVIRONMENTS${CLEAR}"; \
    . /home/ubuntu/scripts/x_tools.sh && \
    export CONFIG_DIR=/home/ubuntu/config && \
    export SCRIPT_DIR=/home/ubuntu/scripts && \
    x_env_init prod 3.10 && \
    x_env_init prod 3.9

# install prod cli
RUN echo "\n${CYAN}INSTALL PROD CLI${CLEAR}"; \
    cp /home/ubuntu/scripts/prod-cli /home/ubuntu/.local/bin/hidebound && \
    chmod 755 /home/ubuntu/.local/bin/hidebound

# build jupyter lab
RUN echo "\n${CYAN}BUILD JUPYTER LAB${CLEAR}"; \
    . /home/ubuntu/scripts/x_tools.sh && \
    export CONFIG_DIR=/home/ubuntu/config && \
    export SCRIPT_DIR=/home/ubuntu/scripts && \
    x_env_activate_dev && \
    jupyter lab build

USER root

# add s6 service and init scripts
COPY --chown=ubuntu:ubuntu --chmod=755 scripts/s_tools.sh /home/ubuntu/scripts/
RUN echo "\n${CYAN}SETUP S6 SERVICES${CLEAR}"; \
    . /home/ubuntu/scripts/s_tools.sh && \
    s_setup_services

# chown /var/log
RUN echo "\n${CYAN}CHOWN /VAR/LOG${CLEAR}"; \
    chown ubuntu:ubuntu /var/log

USER ubuntu
WORKDIR /home/ubuntu

# cleanup dirs
RUN echo "\n${CYAN}REMOVE DIRECTORIES${CLEAR}"; \
    rm -rf /home/ubuntu/config /home/ubuntu/scripts

ENV REPO='hidebound'
ENV PYTHONPATH ":/home/ubuntu/$REPO/python:/home/ubuntu/.local/lib"
ENV PYTHONPYCACHEPREFIX "/home/ubuntu/.python_cache"
ENV HOME /home/ubuntu
ENV JUPYTER_RUNTIME_DIR /tmp/jupyter_runtime

EXPOSE 8888/tcp
ENTRYPOINT ["/init"]
