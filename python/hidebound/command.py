from pprint import pprint
import os
import subprocess

import click
# ------------------------------------------------------------------------------

'''
Command line interface to hidebound application
'''


@click.group()
def main():
    pass


@main.command()
@click.option(
    '--debug',
    is_flag=True,
    help="Runs server in debug mode."
)
def server(debug):
    # type: (bool) -> None
    '''
        Runs a hidebound server.
    '''
    os.environ['HIDEBOUND_TESTING'] = 'False'
    import hidebound.server.app as hba
    hba.APP.run_server(debug=debug, host=hba.EP.host, port=hba.EP.port)


@main.command()
def config():
    # type: () -> None
    '''
        Prints hidebound config.
    '''
    os.environ['HIDEBOUND_TESTING'] = 'True'
    import hidebound.server.app as hba
    app = hba.APP.server
    config = app.extensions['hidebound'].get_config(app)
    pprint(config, indent=4)


@main.command()
def bash_completion():
    '''
        BASH completion code to be written to a _hidebound completion file.
    '''
    cmd = '_HIDEBOUND_COMPLETE=bash_source lunchbox'
    result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result.wait()
    click.echo(result.stdout.read())


@main.command()
def zsh_completion():
    '''
        ZSH completion code to be written to a _hidebound completion file.
    '''
    cmd = '_HIDEBOUND_COMPLETE=zsh_source lunchbox'
    result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    result.wait()
    click.echo(result.stdout.read())


if __name__ == '__main__':
    main()
