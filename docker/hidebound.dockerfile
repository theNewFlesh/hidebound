FROM ubuntu:18.04

WORKDIR /root

# coloring syntax for headers
ARG CYAN='\033[0;36m'
ARG NO_COLOR='\033[0m'

# update ubuntu and install basic dependencies
RUN echo "\n${CYAN}INSTALL GENERIC DEPENDENCIES${NO_COLOR}"; \
    apt update && \
    apt install -y \
    curl \
    git \
    parallel \
    python3-dev \
    software-properties-common \
    tree \
    vim \
    wget

# install python3.7 and pip
ADD https://bootstrap.pypa.io/get-pip.py get-pip.py
RUN echo "\n${CYAN}SETUP PYTHON3.7${NO_COLOR}"; \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt update && \
    apt install -y python3.7 && \
    python3.7 get-pip.py && \
    rm -rf /root/get-pip.py

# DEBIAN_FRONTEND needed by texlive to install non-interactively
ARG DEBIAN_FRONTEND=noninteractive
RUN echo "\n${CYAN}INSTALL NODE.JS DEPENDENCIES${NO_COLOR}"; \
    curl -sL https://deb.nodesource.com/setup_10.x | bash - && \
    apt upgrade -y && \
    echo "\n${CYAN}INSTALL JUPYTERLAB DEPENDENCIES${NO_COLOR}"; \
    apt install -y \
    nodejs && \
    rm -rf /var/lib/apt/lists/*

# install python dependencies
COPY ./dev_requirements.txt /root/dev_requirements.txt
COPY ./prod_requirements.txt /root/prod_requirements.txt
RUN echo "\n${CYAN}INSTALL PYTHON DEPENDECIES${NO_COLOR}"; \
    apt update && \
    apt install -y \
        graphviz \
        python3-pydot && \
    pip3.7 install -r dev_requirements.txt && \
    pip3.7 install -r prod_requirements.txt;
RUN rm -rf /root/dev_requirements;

# added aliases to bashrc
WORKDIR /root
RUN echo "\n${CYAN}CONFIGURE BASHRC${NO_COLOR}"; \
    echo 'export PYTHONPATH="/root/hidebound/python"' >> /root/.bashrc;

# install jupyter lab extensions
ENV NODE_OPTIONS="--max-old-space-size=8192"
RUN echo "\n${CYAN}INSTALL JUPYTER LAB EXTENSIONS${NO_COLOR}"; \
    jupyter labextension install \
    --dev-build=False \
    nbdime-jupyterlab \
    @jupyterlab/toc \
    @oriolmirosa/jupyterlab_materialdarker \
    @ryantam626/jupyterlab_sublime \
    @jupyterlab/plotly-extension

ENV PYTHONPATH "${PYTHONPATH}:/root/hidebound/python"
