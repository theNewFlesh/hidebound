import os
import subprocess
from pathlib import Path

import click
import lunchbox.theme as lbc
import yaml
# ------------------------------------------------------------------------------

'''
Command line interface to hidebound application
'''

click.Context.formatter_class = lbc.ThemeFormatter


@click.group()
def main():
    pass


@main.command()
def bash_completion():
    '''
    {white}BASH completion code to be written to a _hidebound completion
    file.{clear}
    '''
    cmd = '_HIDEBOUND_COMPLETE=bash_source hidebound'
    result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result.wait()
    click.echo(result.stdout.read())


@main.command()
def config():
    # type: () -> None
    '''
    {white}Prints hidebound config.{clear}
    '''
    os.environ['HIDEBOUND_TESTING'] = 'True'
    import hidebound.server.app as hba
    app = hba.APP.server
    config = app.extensions['hidebound'].get_config(app)
    config = yaml.safe_dump(config, indent=4)
    print(config)


@main.command()
@click.option(
    '--port', type=int, default=8080, help='Server port. Default: 8080.'
)
@click.option(
    '--timeout', type=int, default=0, help='Gunicorn timeout. Default: 0.'
)
@click.option(
    '--testing', type=bool, default=False, is_flag=True,
    help='Testing mode. Default: False.'
)
@click.option(
    '--debug', type=bool, default=False, is_flag=True,
    help='Debug mode (no gunicorn). Default: False.'
)
def serve(port, timeout, testing, debug):
    # type: (int, int, bool, bool) -> None
    '''
    {white}Runs a hidebound server.{clear}
    '''
    import hidebound.server.app as hba
    os.environ['HIDEBOUND_TESTING'] = str(testing)
    fp = Path(Path(__file__).parent, 'server').as_posix()
    cmd = f'cd {fp} && '
    if debug:
        cmd += 'python3 app.py'
    else:
        cmd += f'gunicorn --bind {hba.EP.host}:{port} --timeout {timeout} app:SERVER'
    proc = subprocess.Popen(cmd, shell=True)
    proc.wait()


@main.command()
def zsh_completion():
    '''
    {white}ZSH completion code to be written to a _hidebound completion
    file.{clear}
    '''
    cmd = '_HIDEBOUND_COMPLETE=zsh_source hidebound'
    result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result.wait()
    click.echo(result.stdout.read())


if __name__ == '__main__':
    main()
