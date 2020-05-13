# Hidebound
A local database service for converting directories of arbitrary files into validated assets and derived metadata for export to databases like AWS S3 and MongoDB.

See **[documentation](https://thenewflesh.github.io/hidebound/)** for details.

# Installation
`pip install hidebound`

# For Developers
## Installation
1. Install [docker](https://docs.docker.com/v17.09/engine/installation)
2. Install [docker-machine](https://docs.docker.com/machine/install-machine)
   (if running on macOS or Windows)
3. Ensure docker-machine has at least 4 GB of memory allocated to it.
4. `cd hidebound`
5. `chmod +x bin/hidebound`
6. `bin/hidebound start`

The service should take a few minutes to start up.

Run `bin/hidebound --help` for more help on the command line tool.
