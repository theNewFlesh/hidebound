FROM ubuntu:18.04

WORKDIR /home/ubuntu

# coloring syntax for headers
ARG CYAN='\033[0;36m'
ARG NO_COLOR='\033[0m'

# update ubuntu and install basic dependencies
RUN echo "\n${CYAN}INSTALL GENERIC DEPENDENCIES${NO_COLOR}"; \
    apt update && \
    apt install -y \
    python3-dev \
    software-properties-common

# install python3.7 and pip
RUN echo "\n${CYAN}SETUP PYTHON3.7${NO_COLOR}"; \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt update && \
    apt install -y python3.7 && \
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
RUN echo "\n${CYAN}INSTALL HIDEBOUND${NO_COLOR}"; \
    apt update && \
    apt install -y \
    graphviz \
    python3-pydot && \
    pip3.7 install hidebound

ENTRYPOINT [\
    "python3.7",\
    "/usr/local/lib/python3.7/dist-packages/hidebound/server/app.py"\
]
