# Introduction
A local database service for converting directories of arbitrary files into validated assets and derived metadata for export to databases like AWS S3 and MongoDB.

See [documentation](https://thenewflesh.github.io/hidebound/) for details.

# Installation
### Python
`pip install hidebound`

### Docker
1. Install [docker](https://docs.docker.com/v17.09/engine/installation)
2. Install [docker-machine](https://docs.docker.com/machine/install-machine)
   (if running on macOS or Windows)
4. `docker pull thenewflesh/hidebound:latest`

### Docker For Developers
1. Install [docker](https://docs.docker.com/v17.09/engine/installation)
2. Install [docker-machine](https://docs.docker.com/machine/install-machine)
   (if running on macOS or Windows)
3. Ensure docker-machine has at least 4 GB of memory allocated to it.
4. `git clone git@github.com:theNewFlesh/hidebound.git`
5. `cd hidebound`
6. `chmod +x bin/hidebound`
7. `bin/hidebound start`

The service should take a few minutes to start up.

Run `bin/hidebound --help` for more help on the command line tool.
