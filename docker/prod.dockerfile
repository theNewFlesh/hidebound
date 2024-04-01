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
        --gid $GID_ ubuntu
WORKDIR /home/ubuntu

# update ubuntu and install basic dependencies
RUN echo "\n${CYAN}INSTALL GENERIC DEPENDENCIES${CLEAR}"; \
    apt update && \
    apt install -y \
        curl \
        software-properties-common && \
    rm -rf /var/lib/apt/lists/*

# install python3.10 and pip
RUN echo "\n${CYAN}SETUP PYTHON3.10${CLEAR}"; \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt update && \
    apt install --fix-missing -y python3.10 && \
    rm -rf /var/lib/apt/lists/* && \
    curl -fsSL https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    python3.10 get-pip.py && \
    rm -rf /home/ubuntu/get-pip.py

# install tini
RUN echo "\n${CYAN}INSTALL TINI${CLEAR}"; \
    curl -LJ https://github.com/krallin/tini/releases/download/v0.19.0/tini \
        -o /usr/bin/tini && \
    chown ubuntu:ubuntu /usr/bin/tini && \
    chmod +x /usr/bin/tini

# chown /var/log
RUN echo "\n${CYAN}CHOWN /VAR/LOG${CLEAR}"; \
    chown ubuntu:ubuntu /var/log

# install hidebound
USER ubuntu
RUN echo "\n${CYAN}INSTALL HIDEBOUND{CLEAR}"; \
    pip3.10 install --user --upgrade hidebound

ENV PATH="/home/ubuntu/.local/bin:$PATH"
EXPOSE 8080
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD [ "hidebound", "serve" ]
