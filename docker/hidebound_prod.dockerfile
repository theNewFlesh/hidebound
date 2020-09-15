FROM ubuntu:18.04

WORKDIR /root

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
ADD https://bootstrap.pypa.io/get-pip.py get-pip.py
RUN echo "\n${CYAN}SETUP PYTHON3.7${NO_COLOR}"; \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt update && \
    apt install -y python3.7 && \
    python3.7 get-pip.py && \
    rm -rf /root/get-pip.py

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

# install python dependencies
# COPY ./ /root/hidebound
# RUN echo "\n${CYAN}INSTALL PYTHON DEPENDECIES${NO_COLOR}"; \
#     apt update && \
#     apt install -y \
#         graphviz \
#         python3-pydot && \
#     pip3.7 install -r /root/hidebound/docker/prod_requirements.txt;

# # added aliases to bashrc
# RUN echo "\n${CYAN}CONFIGURE BASHRC${NO_COLOR}"; \
#     echo 'export PYTHONPATH="/root/hidebound/python"' >> /root/.bashrc; \
#     echo 'export REPO_ENV=True' >> /root/.bashrc;

# ENV PYTHONPATH "${PYTHONPATH}:/root/hidebound/python"
# ENV REPO_ENV True

# ENTRYPOINT [\
#     "python3.7",\
#     "/root/hidebound/python/hidebound/server/app.py"\
# ]

# install hidebound
RUN echo "\n${CYAN}INSTALL HIDEBOUND${NO_COLOR}"; \
    apt update && \
    apt install -y \
        graphviz \
        python3-pydot && \
    pip3.7 install hidebound>=0.7.4;

ENTRYPOINT [\
    "python3.7",\
    "/usr/local/lib/python3.7/dist-packages/hidebound/server/app.py"\
]
