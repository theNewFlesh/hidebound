#!/usr/bin/env python

try:
    # python2.7 doesn't have typing module
    from typing import Any, List, Tuple
except ImportError:
    pass

import argparse
import os
import re

# python2.7 doesn't have pathlib module
REPO_PATH = os.path.join(os.sep, *os.path.realpath(__file__).split(os.sep)[:-2])
REPO = os.path.split(REPO_PATH)[-1]
GITHUB_USER = 'theNewFlesh'
USER = 'ubuntu:ubuntu'
PORT = 8080
# ------------------------------------------------------------------------------

'''
A CLI for developing and deploying an app deeply integrated with this
repository's structure. Written to be python version agnostic.
'''


def get_info():
    # type: () -> Tuple[str, list]
    '''
    Parses command line call.

    Returns:
        tuple[str]: Mode and arguments.
    '''
    desc = 'A CLI for developing and deploying the {repo} app.'.format(
        repo=REPO
    )
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description=desc,
        usage='\n\tpython cli.py COMMAND [-a --args]=ARGS [-h --help]'
    )

    parser.add_argument(
        'command',
        metavar='command',
        type=str,
        nargs=1,
        action='store',
        help='''Command to run in {repo} app.
    build-package        - Build production version of repo for publishing
    build-prod           - Publish pip package of repo to PyPi
    build-publish        - Run production tests first then publish pip package of repo to PyPi
    build-test           - Build test version of repo for prod testing
    docker-build         - Build image of {repo}
    docker-build-prod    - Build production image of {repo}
    docker-container     - Display the Docker container id of {repo}
    docker-coverage      - Generate coverage report for {repo}
    docker-destroy       - Shutdown {repo} container and destroy its image
    docker-destroy-prod  - Shutdown {repo} production container and destroy its image
    docker-image         - Display the Docker image id of {repo}
    docker-prod          - Start {repo} production container
    docker-push          - Push {repo} production image to Dockerhub
    docker-remove        - Remove {repo} Docker image
    docker-restart       - Restart {repo} container
    docker-start         - Start {repo} container
    docker-stop          - Stop {repo} container
    docs                 - Generate sphinx documentation
    docs-architecture    - Generate architecture.svg diagram from all import statements
    docs-full            - Generate documentation, coverage report, diagram and code
    docs-metrics         - Generate code metrics report, plots and tables
    library-add          - Add a given package to a given dependency group
    library-graph-dev    - Graph dependencies in dev environment
    library-graph-prod   - Graph dependencies in prod environment
    library-install-dev  - Install all dependencies into dev environment
    library-install-prod - Install all dependencies into prod environment
    library-list-dev     - List packages in dev environment
    library-list-prod    - List packages in prod environment
    library-lock-dev     - Resolve dev.lock file
    library-lock-prod    - Resolve prod.lock file
    library-remove       - Remove a given package from a given dependency group
    library-search       - Search for pip packages
    library-sync-dev     - Sync dev environment with packages listed in dev.lock
    library-sync-prod    - Sync prod environment with packages listed in prod.lock
    library-update       - Update dev dependencies
    session-app          - Run app
    session-lab          - Run jupyter lab server
    session-python       - Run python session with dev dependencies
    state                - State of {repo}
    test-coverage        - Generate test coverage report
    test-dev             - Run all tests
    test-fast            - Test all code excepts tests marked with SKIP_SLOWS_TESTS decorator
    test-lint            - Run linting and type checking
    test-prod            - Run tests across all support python versions
    version              - Full resolution of repo: dependencies, linting, tests, docs, etc
    version-bump-major   - Bump pyproject major version
    version-bump-minor   - Bump pyproject minor version
    version-bump-patch   - Bump pyproject patch version
    zsh                  - Run ZSH session inside {repo} container
    zsh-complete         - Generate oh-my-zsh completions
    zsh-root             - Run ZSH session as root inside {repo} container
'''.format(repo=REPO))

    parser.add_argument(
        '-a',
        '--args',
        metavar='args',
        type=str,
        nargs='+',
        action='store',
        help='Additional arguments to be passed. Be sure to include hyphen prefixes.'
    )

    temp = parser.parse_args()
    mode = temp.command[0]
    args = []
    if temp.args is not None:
        args = re.split(' +', temp.args[0])

    return mode, args


def resolve(commands):
    # type: (List[str]) -> str
    '''
    Convenience function for creating single commmand from given commands and
    resolving '{...}' substrings.

    Args:
        commands (list[str]): List of commands.

    Returns:
        str: Resolved command.
    '''
    cmd = ' && '.join(commands)

    all_ = dict(
        black='\033[0;30m',
        blue='\033[0;34m',
        clear='\033[0m',
        cyan='\033[0;36m',
        green='\033[0;32m',
        purple='\033[0;35m',
        red='\033[0;31m',
        white='\033[0;37m',
        yellow='\033[0;33m',
        github_user=GITHUB_USER,
        port=str(PORT),
        pythonpath='{PYTHONPATH}',
        repo_path=REPO_PATH,
        repo=REPO,
        repo_=re.sub('-', '_', REPO),
        user=USER,
    )
    args = {}
    for k, v in all_.items():
        if '{' + k + '}' in cmd:
            args[k] = v

    cmd = cmd.format(**args)
    return cmd


def line(text, sep=' '):
    # type: (str, str) -> str
    '''
    Convenience function for formatting a given block of text as series of
    commands.

    Args:
        text (text): Block of text.
        sep (str, optional): Line separator. Default: ' '.

    Returns:
        str: Formatted command.
    '''
    output = re.sub('^\n|\n$', '', text)  # type: Any
    output = output.split('\n')
    output = [re.sub('^ +| +$', '', x) for x in output]
    output = sep.join(output) + sep
    return output


# SUBCOMMANDS-------------------------------------------------------------------
def enter_repo():
    # type: () -> str
    '''
    Returns:
        str: Command to enter repo.
    '''
    return 'export CWD=`pwd` && cd {repo_path}'


def exit_repo():
    # type: () -> str
    '''
    Returns:
        str: Command to return to original directory.
    '''
    return 'cd $CWD'


def start():
    # type: () -> str
    '''
    Returns:
        str: Command to start container if it is not yet running.
    '''
    cmds = [
        line('''
            export STATE=`docker ps
                -a
                -f name=^{repo}$
                -f status=running
                --format='{{{{{{{{.Status}}}}}}}}'`
        '''),
        line('''
            if [ -z "$STATE" ];
                then cd docker;
                docker compose
                    -p {repo}
                    -f {repo_path}/docker/docker-compose.yml up
                    --detach;
                cd ..;
            fi
        '''),
    ]
    return resolve(cmds)


def stop():
    # type: () -> str
    '''
    Returns:
        str: Command to shutdown container.
    '''
    cmd = line('''
        cd docker;
        docker compose
            -p {repo}
            -f {repo_path}/docker/docker-compose.yml
            down;
        cd ..
    ''')
    return cmd


def remove_container():
    # type: () -> str
    '''
    Returns:
        str: Command to remove container.
    '''
    return 'docker container rm --force {repo}'


def docker_exec():
    # type: () -> str
    '''
    Returns:
        str: Partial command to call 'docker exec'.
    '''
    cmd = line('''
        docker exec
            --interactive
            --tty
            --user {user}
    ''')
    return cmd


def version_variable():
    # type: () -> str
    '''
    Returns:
        str: Command to set version variable from pyproject.toml.
    '''
    return line('''
        export VERSION=`cat docker/config/pyproject.toml
            | grep -E '^version *='
            | awk '{{print $3}}'
            | sed 's/\"//g'`
    ''')


def x_tools(command, args=[]):
    # type: (str, list[str]) -> str
    '''
    Creates a x_tools command string.

    Args:
        command (str): x_tools command
        args (list, optional): List of arguments to be passed to the command.
            Default: []

    Returns:
        str: x_tools command.
    '''

    cmd = 'source /home/ubuntu/.zshrc && {cmd}'.format(cmd=command)
    if args != []:
        cmd = cmd + ' ' + ' '.join(args)
    cmd = '"{cmd}"'.format(cmd=cmd)
    return cmd


# COMMANDS----------------------------------------------------------------------
def build_dev_command():
    # type: () -> str
    '''
    Returns:
        str: Command to build dev image.
    '''
    cmds = [
        enter_repo(),
        line('''
            cd docker;
            docker build
                --file dev.dockerfile
                --tag {repo}:dev .;
            cd ..
        '''),
        exit_repo(),
    ]
    return resolve(cmds)


def build_prod_command():
    # type: () -> str
    '''
    Returns:
        str: Command to build prod image.
    '''
    cmds = [
        enter_repo(),
        version_variable(),
        line('''
            cd docker;
            docker build
                --force-rm
                --no-cache
                --file prod.dockerfile
                --tag {github_user}/{repo}:$VERSION .;
            cd ..
        '''),
        exit_repo(),
    ]
    return resolve(cmds)


def container_id_command():
    # type: () -> str
    '''
    Returns:
        str: Command to get docker container id.
    '''
    cmds = [
        "docker ps -a --filter name=^{repo}$ --format '{{{{.ID}}}}'"
    ]
    return resolve(cmds)


def destroy_dev_command():
    # type: () -> str
    '''
    Returns:
        str: Command to destroy dev container and image.
    '''
    cmds = [
        enter_repo(),
        stop(),
        remove_container(),
        'docker image rm --force {repo}:dev',
        exit_repo(),
    ]
    return resolve(cmds)


def destroy_prod_command():
    # type: () -> str
    '''
    Returns:
        str: Command to destroy prod image.
    '''
    cmds = [
        "export PROD_CID=`docker ps --filter name=^{repo}-prod$ --format '{{{{.ID}}}}'`",
        "export PROD_IID=`docker images {github_user}/{repo} --format '{{{{.ID}}}}'`",
        'docker container stop $PROD_CID',
        'docker image rm --force $PROD_IID',
    ]
    return resolve(cmds)


def image_id_command():
    # type: () -> str
    '''
    Returns:
        str: Command to get docker image id.
    '''
    cmds = [
        enter_repo(),
        start(),
        "docker images {repo} --format '{{{{.ID}}}}'",
        exit_repo(),
    ]
    return resolve(cmds)


def prod_command(args):
    # type: (list) -> str
    '''
    Returns:
        str: Command to start prod container.
    '''
    if args == ['']:
        cmds = [
            line('''
                echo "Please provide a directory to map into the container
                after the {cyan}-a{clear} flag."
            ''')
        ]
        return resolve(cmds)

    run = 'docker run --volume {}:/mnt/storage'.format(args[0])
    cmds = [
        enter_repo(),
        version_variable(),
        line(run + '''
            --rm
            --publish {port}:{port}
            --name {repo}-prod
            {github_user}/{repo}:$VERSION
        '''),
        exit_repo(),
    ]
    return resolve(cmds)


def push_command():
    # type: () -> str
    '''
    Returns:
        str: Command to push prod docker image to dockerhub.
    '''
    cmds = [
        enter_repo(),
        version_variable(),
        start(),
        'docker push {github_user}/{repo}:$VERSION',
        exit_repo(),
    ]
    return resolve(cmds)


def remove_command():
    # type: () -> str
    '''
    Returns:
        str: Command to remove container.
    '''
    cmds = [
        enter_repo(),
        remove_container(),
        exit_repo(),
    ]
    return resolve(cmds)


def restart_command():
    # type: () -> str
    '''
    Returns:
        str: Command to restart container.
    '''
    cmds = [
        enter_repo(),
        line('''
            cd docker;
            docker compose
                -p {repo}
                -f {repo_path}/docker/docker-compose.yml
                restart;
            cd ..
        '''),
        exit_repo(),
    ]
    return resolve(cmds)


def start_command():
    # type: () -> str
    '''
    Returns:
        str: Command to start container.
    '''
    cmds = [
        enter_repo(),
        start(),
    ]
    return resolve(cmds)


def state_command():
    # type: () -> str
    '''
    Returns:
        str: Command to get state of app.
    '''
    cmds = [
        enter_repo(),
        version_variable(),
        'export IMAGE_EXISTS=`docker images {repo} | grep -v REPOSITORY`',
        'export CONTAINER_EXISTS=`docker ps -a -f name=^{repo}$ | grep -v CONTAINER`',
        'export RUNNING=`docker ps -a -f name=^{repo}$ -f status=running | grep -v CONTAINER`',
        line(r'''
            export PORTS=`
                cat docker/docker-compose.yml |
                grep -E ' - "....:...."' |
                sed s'/.* - "//g' |
                sed 's/"//g' |
                sed 's/^/{blue}/g' |
                sed 's/:/{clear}-->/g' |
                awk 1 ORS=' '
            `
        '''),
        line('''
            if [ -z "$IMAGE_EXISTS" ];
                then export IMAGE_STATE="{red}absent{clear}";
            else
                export IMAGE_STATE="{green}present{clear}";
            fi;
            if [ -z "$CONTAINER_EXISTS" ];
                then export CONTAINER_STATE="{red}absent{clear}";
            elif [ -z "$RUNNING" ];
                then export CONTAINER_STATE="{red}stopped{clear}";
            else
                export CONTAINER_STATE="{green}running{clear}";
            fi
        '''),
        line('''echo
            "app: {cyan}{repo}{clear} -
            version: {yellow}$VERSION{clear} -
            image: $IMAGE_STATE -
            container: $CONTAINER_STATE -
            ports: {blue}$PORTS{clear}"
        '''),
        exit_repo(),
    ]
    return resolve(cmds)


def stop_command():
    # type: () -> str
    '''
    Returns:
        str: Command to stop container.
    '''
    cmds = [
        enter_repo(),
        stop(),
        exit_repo(),
    ]
    return resolve(cmds)


def x_tools_command(command, args=[]):
    # type: (str, list[str]) -> str
    '''
    Runs a x_tools command.

    Args:
        command (str): x_tools command
        args (list, optional): List of arguments to be passed to the command.
            Default: []

    Returns:
        str: x_tools command.
    '''
    cmds = [
        enter_repo(),
        start(),
        docker_exec() + ' {repo} zsh -c ' + x_tools(command, args),
        exit_repo(),
    ]
    return resolve(cmds)


def zsh_command():
    # type: () -> str
    '''
    Returns:
        str: Command to run a zsh session inside container.
    '''
    cmds = [
        enter_repo(),
        start(),
        docker_exec() + ' {repo} zsh',
        exit_repo(),
    ]
    return resolve(cmds)


def zsh_complete_command():
    # type: () -> str
    '''
    Returns:
        str: Command to generate and install zsh completions.
    '''
    cmds = [
        'mkdir -p ~/.oh-my-zsh/custom/completions',
        'export _COMP=~/.oh-my-zsh/custom/completions/_{repo}',
        'touch $_COMP',
        "echo 'fpath=(~/.oh-my-zsh/custom/completions $fpath)' >> ~/.zshrc",
        'echo "#compdef {repo} rec" > $_COMP',
        'echo "" >> $_COMP',
        'echo "local -a _subcommands" >> $_COMP',
        'echo "_subcommands=(" >> $_COMP',
        line('''
            bin/{repo} --help
                | grep '    - '
                | sed -E 's/ +- /:/g'
                | sed -E 's/^ +//g'
                | sed -E "s/(.*)/    '\\1'/g"
                | parallel "echo {{}} >> $_COMP"
        '''),
        'echo ")" >> $_COMP',
        'echo "" >> $_COMP',
        'echo "local expl" >> $_COMP',
        'echo "" >> $_COMP',
        'echo "_arguments \\\\" >> $_COMP',
        'echo "    \'(-h --help)\'{{-h,--help}}\'[show help message]\' \\\\" >> $_COMP',
        'echo "    \'(-d --dryrun)\'{{-d,--dryrun}}\'[print command]\' \\\\" >> $_COMP',
        'echo "    \'*:: :->subcmds\' && return 0" >> $_COMP',
        'echo "\n" >> $_COMP',
        'echo "if (( CURRENT == 1 )); then" >> $_COMP',
        'echo "    _describe -t commands \\"{repo} subcommand\\" _subcommands\" >> $_COMP',
        'echo "    return" >> $_COMP',
        'echo "fi" >> $_COMP',
    ]
    return resolve(cmds)


def zsh_root_command():
    # type: () -> str
    '''
    Returns:
        str: Command to run a zsh session as root inside container.
    '''
    return re.sub('ubuntu:ubuntu', 'root:root', zsh_command())


def get_illegal_mode_command():
    # type: () -> str
    '''
    Returns:
        str: Command to report that the mode given is illegal.
    '''
    cmds = [
        line('''
            echo "That is not a legal command.
            Please call {cyan}{repo} --help{clear} to see a list of legal
            commands."
        ''')
    ]
    return resolve(cmds)


# MAIN--------------------------------------------------------------------------
def main():
    # type: () -> None
    '''
    Print different commands to stdout depending on mode provided to command.
    '''
    mode, args = get_info()
    lut = {
        'build-package': x_tools_command('x_build_package', args),
        'build-prod': x_tools_command('x_build_prod', args),
        'build-publish': x_tools_command('x_build_publish', args),
        'build-test': x_tools_command('x_build_test', args),
        'docker-build': build_dev_command(),
        'docker-build-prod': build_prod_command(),
        'docker-container': container_id_command(),
        'docker-destroy': destroy_dev_command(),
        'docker-destroy-prod': destroy_prod_command(),
        'docker-image': image_id_command(),
        'docker-prod': prod_command(args),
        'docker-push': push_command(),
        'docker-remove': remove_command(),
        'docker-restart': restart_command(),
        'docker-start': start_command(),
        'docker-stop': stop_command(),
        'docs': x_tools_command('x_docs', args),
        'docs-architecture': x_tools_command('x_docs_architecture', args),
        'docs-full': x_tools_command('x_docs_full', args),
        'docs-metrics': x_tools_command('x_docs_metrics', args),
        'library-add': x_tools_command('x_library_add', args),
        'library-graph-dev': x_tools_command('x_library_graph_dev', args),
        'library-graph-prod': x_tools_command('x_library_graph_prod', args),
        'library-install-dev': x_tools_command('x_library_install_dev', args),
        'library-install-prod': x_tools_command('x_library_install_prod', args),
        'library-list-dev': x_tools_command('x_library_list_dev', args),
        'library-list-prod': x_tools_command('x_library_list_prod', args),
        'library-lock-dev': x_tools_command('x_library_lock_dev', args),
        'library-lock-prod': x_tools_command('x_library_lock_prod', args),
        'library-remove': x_tools_command('x_library_remove', args),
        'library-search': x_tools_command('x_library_search', args),
        'library-sync-dev': x_tools_command('x_library_sync_dev', args),
        'library-sync-prod': x_tools_command('x_library_sync_prod', args),
        'library-update': x_tools_command('x_library_update', args),
        'session-app': x_tools_command('x_session_app', args),
        'session-lab': x_tools_command('x_session_lab', args),
        'session-python': x_tools_command('x_session_python', args),
        'state': state_command(),
        'test-coverage': x_tools_command('x_test_coverage', args),
        'test-dev': x_tools_command('x_test_dev', args),
        'test-fast': x_tools_command('x_test_fast', args),
        'test-lint': x_tools_command('x_test_lint', args),
        'test-prod': x_tools_command('x_test_prod', args),
        'version': x_tools_command('x_version', args),
        'version-bump-major': x_tools_command('x_version_bump_major', args),
        'version-bump-minor': x_tools_command('x_version_bump_minor', args),
        'version-bump-patch': x_tools_command('x_version_bump_patch', args),
        'zsh': zsh_command(),
        'zsh-complete': zsh_complete_command(),
        'zsh-root': zsh_root_command(),
    }
    cmd = lut.get(mode, get_illegal_mode_command())

    # print is used instead of execute because REPO_PATH and USER do not
    # resolve in a subprocess and subprocesses do not give real time stdout.
    # So, running `command up` will give you nothing until the process ends.
    # `eval "[generated command] $@"` resolves all these issues.
    print(cmd)


if __name__ == '__main__':
    main()
