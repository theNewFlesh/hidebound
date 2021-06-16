#!/usr/bin/env python

from typing import Any, List, Tuple

from pathlib import Path
import argparse
import re

# set's REPO to whatever the repository is named
REPO = Path(__file__).parents[1].absolute().name
REPO_PATH = Path(__file__).parents[1].absolute().as_posix()
GITHUB_USER = 'thenewflesh'
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

    app          - Run Flask app inside {repo} container
    build        - Build image of {repo}
    build-prod   - Build production image of {repo}
    container    - Display the Docker container id for {repo} app
    coverage     - Generate coverage report for {repo} app
    destroy      - Shutdown {repo} app and destroy its Docker image
    destroy-prod - Shutdown {repo} production app and destroy its Docker image
    docs         - Generate documentation for {repo} app
    fast-test    - Run testing on {repo} app skipping tests marked as slow
    full-docs    - Generates documentation, coverage report and metrics
    image        - Display the Docker image id for {repo} app
    lab          - Start a Jupyter lab server
    lint         - Run linting and type checking on {repo} app code
    package      - Build {repo} pip package
    prod         - Start {repo} production app
    publish      - Publish repository to python package index.
    push         - Push production of {repo} image to Dockerhub
    python       - Run python interpreter session inside {repo} container
    remove       - Remove {repo} app Docker image
    restart      - Restart {repo} app
    requirements - Write frozen requirements to disk
    start        - Start {repo} app
    state        - State of {repo} app
    stop         - Stop {repo} app
    test         - Run testing on {repo} app
    tox          - Run tox tests on {repo}
    version-up   - Updates version and runs full-docs and requirements
    zsh          - Run ZSH session inside {repo} container
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
        user=USER,
    )
    args = {}
    for k, v in all_.items():
        if '{' + k + '}' in cmd:
            args[k] = v

    cmd = cmd.format(**args)
    return cmd


def line(text):
    # type: (str) -> str
    '''
    Convenience function for formatting a given block of text as series of
    commands.

    Args:
        text (text): Block of text.

    Returns:
        str: Formatted command.
    '''
    output = re.sub('^\n|\n$', '', text)  # type: Any
    output = output.split('\n')
    output = [re.sub('^ +| +$', '', x) for x in output]
    output = ' '.join(output) + ' '
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
                -f name={repo}
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


def version_variable():
    # type: () -> str
    '''
    Returns:
        str: Command to set version variable from pip/version.txt.
    '''
    return 'export VERSION=`cat pip/version.txt`'


def make_docs_dir():
    # type: () -> str
    '''
    Returns:
        str: Command to create docs directory in repo.
    '''
    cmd = line('''
        docker exec
            --interactive
            --tty
            --user {user}
            -e PYTHONPATH="${pythonpath}:/home/ubuntu/{repo}/python"
            -e REPO_ENV=True {repo}
            mkdir -p /home/ubuntu/{repo}/docs
    ''')
    return cmd


def docker_down():
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


def coverage():
    # type: () -> str
    '''
    Returns:
        str: Partial command to get generate coverage report.
    '''
    cmd = line(
        docker_exec() + '''-e REPO_ENV=True {repo}
            pytest
                /home/ubuntu/{repo}/python
                -c /home/ubuntu/{repo}/docker/pytest.ini
                --cov /home/ubuntu/{repo}/python
                --cov-config /home/ubuntu/{repo}/docker/pytest.ini
                --cov-report html:/home/ubuntu/{repo}/docs/htmlcov
                --headless'''
    )
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
            -e PYTHONPATH="${pythonpath}:/home/ubuntu/{repo}/python"
    ''')
    return cmd


def create_package_repo():
    # type: () -> str
    '''
    Returns:
        str: Command to create a temporary repo in /tmp.
    '''
    cmd = line(
        docker_exec() + r'''{repo} zsh -c "
            rm -rf /tmp/{repo} &&
            cp -R /home/ubuntu/{repo}/python /tmp/{repo} &&
            cp /home/ubuntu/{repo}/README.md /tmp/{repo}/README.md &&
            cp /home/ubuntu/{repo}/LICENSE /tmp/{repo}/LICENSE &&
            cp /home/ubuntu/{repo}/pip/MANIFEST.in /tmp/{repo}/MANIFEST.in &&
            cp /home/ubuntu/{repo}/pip/setup.cfg /tmp/{repo}/ &&
            cp /home/ubuntu/{repo}/pip/setup.py /tmp/{repo}/ &&
            cp /home/ubuntu/{repo}/pip/version.txt /tmp/{repo}/ &&
            cp /home/ubuntu/{repo}/docker/dev_requirements.txt /tmp/{repo}/ &&
            cp /home/ubuntu/{repo}/docker/prod_requirements.txt /tmp/{repo}/ &&
            cp -r /home/ubuntu/{repo}/templates /tmp/{repo}/{repo} &&
            cp -r /home/ubuntu/{repo}/resources /tmp/{repo}/{repo} &&
            find /tmp/{repo}/{repo}/resources -type f | grep -vE 'icon|test_'
                | parallel 'rm -rf {{}}' &&
            find /tmp/{repo} | grep -E '.*test.*\.py$|mock.*\.py$|__pycache__'
                | parallel 'rm -rf {{}}' &&
            find /tmp/{repo} -type f | grep __init__.py
                | parallel 'rm -rf {{}};touch {{}}'
        "
    ''')
    return cmd


# COMMANDS----------------------------------------------------------------------
def app_command():
    # type: () -> str
    '''
    Returns:
        str: Command to start app.
    '''
    cmds = [
        enter_repo(),
        start(),
        line(
            docker_exec() + '''
                -e DEBUG_MODE=True
                -e REPO_ENV=True {repo}
                python3.7 /home/ubuntu/{repo}/python/{repo}/server/app.py'''
        ),
        exit_repo(),
    ]
    return resolve(cmds)


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
                --force-rm
                --no-cache
                --file dev.dockerfile
                --tag {repo}:latest .;
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
        "docker ps -a --filter name={repo} --format '{{{{.ID}}}}'"
    ]
    return resolve(cmds)


def coverage_command():
    # type: () -> str
    '''
    Returns:
        str: Command to get generate coverage report.
    '''
    cmds = [
        enter_repo(),
        start(),
        make_docs_dir(),
        coverage(),
        exit_repo(),
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
        docker_down(),
        remove_container(),
        'docker image rm --force {repo}',
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
        "export PROD_CID=`docker ps --filter name={repo}-prod --format '{{{{.ID}}}}'`",
        "export PROD_IID=`docker images {github_user}/{repo} --format '{{{{.ID}}}}'`",
        'docker container stop $PROD_CID',
        'docker image rm --force $PROD_IID',
    ]
    return resolve(cmds)


def docs_command():
    # type: () -> str
    '''
    Returns:
        str: Command to generate documentation.
    '''
    cmds = [
        enter_repo(),
        start(),
        make_docs_dir(),
        line(
            docker_exec() + '''-e REPO_ENV=True {repo}
                 zsh -c "
                    pandoc /home/ubuntu/{repo}/README.md
                        -o /home/ubuntu/{repo}/sphinx/intro.rst;
                    sphinx-build
                        /home/ubuntu/{repo}/sphinx
                        /home/ubuntu/{repo}/docs;
                    cp /home/ubuntu/{repo}/sphinx/style.css
                    /home/ubuntu/{repo}/docs/_static/style.css;
                    touch /home/ubuntu/{repo}/docs/.nojekyll;
                    mkdir -p /home/ubuntu/{repo}/docs/resources;
                "
        '''),
        exit_repo(),
    ]
    return resolve(cmds)


def fast_test_command():
    # type: () -> str
    '''
    Returns:
        str: Command to run test not marked slow.
    '''
    cmds = [
        enter_repo(),
        start(),
        line(
            docker_exec() + '''-e REPO_ENV=True -e SKIP_SLOW_TESTS=true {repo}
                pytest
                    /home/ubuntu/{repo}/python
                    -c /home/ubuntu/{repo}/docker/pytest.ini
                    --headless'''
        ),
        exit_repo(),
    ]
    return resolve(cmds)


def full_docs_command():
    # type: () -> str
    '''
    Generates:

      * documentation
      * code coverage report
      * dependency architecture diagram
      * code metrics plots

    Returns:
        str: Command.
    '''
    cmds = [
        enter_repo(),
        start(),
        make_docs_dir(),
        line(
            docker_exec() + '''-e REPO_ENV=True {repo}
                 zsh -c "
                    pandoc
                        /home/ubuntu/{repo}/README.md
                        -o /home/ubuntu/{repo}/sphinx/intro.rst;
                    sphinx-build
                        /home/ubuntu/{repo}/sphinx
                        /home/ubuntu/{repo}/docs;
                    cp
                        /home/ubuntu/{repo}/sphinx/style.css
                        /home/ubuntu/{repo}/docs/_static/style.css;
                    touch /home/ubuntu/{repo}/docs/.nojekyll;
                    mkdir -p /home/ubuntu/{repo}/docs/resources;
                "
        '''),
        coverage(),
        line(
            docker_exec() + '''-e REPO_ENV=True {repo}
                python3.7 -c "
                    import re;
                    from rolling_pin.repo_etl import RepoETL;
                    etl = RepoETL('/home/ubuntu/{repo}/python');
                    regex = 'test|mock';
                    data = etl._data.copy();
                    func = lambda x: not bool(re.search(regex, x));
                    mask = data.node_name.apply(func);
                    data = data[mask];
                    data.reset_index(inplace=True, drop=True);
                    data.dependencies = data.dependencies.apply(
                        lambda x: list(filter(func, x))
                    );
                    etl._data = data;
                    etl.write(
                        '/home/ubuntu/{repo}/docs/architecture.svg',
                        orient='lr'
                    );
                "
        '''),
        line(
            docker_exec() + '''-e REPO_ENV=True {repo}
                python3.7 -c "
                    from rolling_pin.radon_etl import RadonETL;
                    etl = RadonETL('/home/ubuntu/{repo}/python');
                    etl.write_plots('/home/ubuntu/{repo}/docs/plots.html');
                    etl.write_tables('/home/ubuntu/{repo}/docs');
                "
        '''),
        exit_repo(),
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


def lab_command():
    # type: () -> str
    '''
    Returns:
        str: Command to start jupyter lab.
    '''
    cmds = [
        enter_repo(),
        start(),
        line(
            docker_exec() + '''-e REPO_ENV=True {repo}
                jupyter lab --allow-root --ip=0.0.0.0 --no-browser'''
        ),
        exit_repo(),
    ]
    return resolve(cmds)


def lint_command():
    # type: () -> str
    '''
    Returns:
        str: Command to run linting and type analysis.
    '''
    cmds = [
        enter_repo(),
        start(),
        'echo LINTING',
        line(
            docker_exec() + '''-e REPO_ENV=True {repo}
                flake8
                    /home/ubuntu/{repo}/python
                    --config /home/ubuntu/{repo}/docker/flake8.ini'''
        ),
        'echo TYPE CHECKING',
        line(
            docker_exec() + '''-e REPO_ENV=True {repo}
                mypy
                    /home/ubuntu/{repo}/python
                    --config-file /home/ubuntu/{repo}/docker/mypy.ini'''
        ),
        exit_repo(),
    ]
    return resolve(cmds)


def package_command():
    # type: () -> str
    '''
    Returns:
        str: Command to pip package repo.
    '''
    cmds = [
        enter_repo(),
        start(),
        create_package_repo(),
        docker_exec() + ' -w /tmp/{repo} {repo} python3.7 setup.py sdist',
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


def publish_command():
    # type: () -> str
    '''
    Returns:
        str: Command to publish repo as pip package.
    '''
    cmds = [
        enter_repo(),
        start(),
        line(
            docker_exec() + r'''{repo} zsh -c "
                rm -rf /tmp/{repo} &&
                cp -R /home/ubuntu/{repo}/python /tmp/{repo} &&
                cp -R /home/ubuntu/{repo}/docker/* /tmp/{repo}/ &&
                cp -R /home/ubuntu/{repo}/resources /tmp/{repo}/{repo} &&
                cp /home/ubuntu/{repo}/pip/* /tmp/{repo}/ &&
                cp /home/ubuntu/{repo}/LICENSE /tmp/{repo}/ &&
                cp /home/ubuntu/{repo}/README.md /tmp/{repo}/ &&
                find /tmp/{repo}/{repo}/resources -type f
                    | grep -vE 'icon|test_' | parallel 'rm -rf {{}}' &&
                cp -R /home/ubuntu/{repo}/templates /tmp/{repo}/{repo} &&
                cp -R /home/ubuntu/{repo}/python/conftest.py /tmp/{repo}/ &&
                find /tmp/{repo} | grep -E '__pycache__|\.pyc$'
                    | parallel 'rm -rf' &&
                cd /tmp/{repo} &&
                tox &&
                find {repo_path} | grep -E '__pycache__|\.pyc$'
                    | parallel 'rm -rf {{}}'
            "
        '''),
        create_package_repo(),
        docker_exec() + ' -w /tmp/{repo} {repo} python3.7 setup.py sdist',
        docker_exec() + ' -w /tmp/{repo} {repo} twine upload dist/*',
        docker_exec() + ' {repo} rm -rf /tmp/{repo}',
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


def python_command():
    # type: () -> str
    '''
    Returns:
        str: Command to start python interpreter.
    '''
    cmds = [
        enter_repo(),
        start(),
        docker_exec() + ' -e REPO_ENV=True {repo} python3.7',
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


def requirements_command():
    # type: () -> str
    '''
    Returns:
        str: Command to regenerate frozen_requirements.txt.
    '''
    cmds = [
        enter_repo(),
        start(),
        line(
            docker_exec() + '''-e REPO_ENV=True {repo} zsh -c "
                python3.7 -m pip list --format freeze >
                    /home/ubuntu/{repo}/docker/frozen_requirements.txt"
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
        'export CONTAINER_EXISTS=`docker ps -a -f name={repo} | grep -v CONTAINER`',
        'export RUNNING=`docker ps -a -f name={repo} -f status=running | grep -v CONTAINER`',
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
            "app: {cyan}{repo}{clear}:{yellow}$VERSION{clear} -
            image: $IMAGE_STATE -
            container: $CONTAINER_STATE"
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
        docker_down(),
        exit_repo(),
    ]
    return resolve(cmds)


def test_command():
    # type: () -> str
    '''
    Returns:
        str: Command to run tests.
    '''
    cmds = [
        enter_repo(),
        start(),
        line(
            docker_exec() + '''-e REPO_ENV=True {repo}
                pytest
                    /home/ubuntu/{repo}/python
                    -c /home/ubuntu/{repo}/docker/pytest.ini
                    --headless'''
        ),
        exit_repo(),
    ]
    return resolve(cmds)


def tox_command():
    # type: () -> str
    '''
    Returns:
        str: Command to run tox.
    '''
    cmds = [
        enter_repo(),
        start(),
        line(
            docker_exec() + r'''{repo} zsh -c "
                rm -rf /tmp/{repo} &&
                cp -R /home/ubuntu/{repo}/python /tmp/{repo} &&
                cp -R /home/ubuntu/{repo}/docker/* /tmp/{repo}/ &&
                cp -R /home/ubuntu/{repo}/resources /tmp/{repo}/{repo} &&
                cp /home/ubuntu/{repo}/pip/* /tmp/{repo}/ &&
                cp /home/ubuntu/{repo}/LICENSE /tmp/{repo}/ &&
                cp /home/ubuntu/{repo}/README.md /tmp/{repo}/ &&
                find /tmp/{repo}/{repo}/resources -type f
                    | grep -vE 'icon|test_' | parallel 'rm -rf {{}}' &&
                cp -R /home/ubuntu/{repo}/templates /tmp/{repo}/{repo} &&
                cp -R /home/ubuntu/{repo}/python/conftest.py /tmp/{repo}/ &&
                find /tmp/{repo} | grep -E '__pycache__|\.pyc$'
                    | parallel 'rm -rf' &&
                cd /tmp/{repo} &&
                tox
            "
        '''),
        exit_repo(),
    ]
    return resolve(cmds)


def version_up_command(args):
    # type: (list) -> str
    '''
    Sets pip/version.txt to given value. Then calls full-docs.

    Returns:
        str: Command.
    '''
    if args == ['']:
        cmds = [
            'echo "Please provide a version after the {cyan}-a{clear} flag."'
        ]
        return resolve(cmds)

    cmds = [
        enter_repo(),
        'echo {} > pip/version.txt'.format(args[0]),
        exit_repo(),
    ]
    cmd = resolve(cmds)
    cmd = cmd + ' && ' + full_docs_command()
    return cmd


def zsh_command():
    # type: () -> str
    '''
    Returns:
        str: Command to run a zsh session inside container.
    '''
    cmds = [
        enter_repo(),
        start(),
        docker_exec() + ' -e REPO_ENV=True {repo} zsh',
        exit_repo(),
    ]
    return resolve(cmds)


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
        'app': app_command(),
        'build': build_dev_command(),
        'build-prod': build_prod_command(),
        'container': container_id_command(),
        'coverage': coverage_command(),
        'destroy': destroy_dev_command(),
        'destroy-prod': destroy_prod_command(),
        'docs': docs_command(),
        'fast-test': fast_test_command(),
        'full-docs': full_docs_command(),
        'image': image_id_command(),
        'lab': lab_command(),
        'lint': lint_command(),
        'package': package_command(),
        'prod': prod_command(args),
        'publish': publish_command(),
        'push': push_command(),
        'python': python_command(),
        'remove': remove_command(),
        'requirements': requirements_command(),
        'restart': restart_command(),
        'start': start_command(),
        'state': state_command(),
        'stop': stop_command(),
        'test': test_command(),
        'tox': tox_command(),
        'version-up': version_up_command(args),
        'zsh': zsh_command(),
    }
    cmd = lut.get(mode, get_illegal_mode_command())

    # print is used instead of execute because REPO_PATH and USER do not
    # resolve in a subprocess and subprocesses do not give real time stdout.
    # So, running `command up` will give you nothing until the process ends.
    # `eval "[generated command] $@"` resolves all these issues.
    print(cmd)


if __name__ == '__main__':
    main()
