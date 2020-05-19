from pathlib import Path
import base64
import json
import os

import flasgger as swg
import flask
import jinja2

import hidebound.core.tools as tools
# ------------------------------------------------------------------------------


def get_app(name):
    '''
    Get Flask app.

    Args:
        name (str): App name. Should always be __name__.

    Retruns:
        flask.Flask: Flask app.
    '''
    app = flask.Flask(name)
    swg.Swagger(app)
    return app


def render_template(filename, parameters):
    '''
    Renders a jinja2 template given by filename with given parameters.

    Args:
        filename (str): Filename of template.
        parameters (dict): Dictionary of template parameters.

    Returns:
        str: HTML string.
    '''
    tempdir = tools.relative_path(__file__, '../../../templates').as_posix()
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(tempdir),
        keep_trailing_newline=True
    )
    output = env.get_template(filename).render(parameters).encode('utf-8')
    return output


def parse_json_file_content(raw_content):
    '''
    Parses JSON file content as supplied by HTML request.

    Args:
        raw_content (bytes): Raw JSON file content.

    Raises:
        ValueError: If header is invalid.
        JSONDecodeError: If JSON is invalid.

    Returns:
        dict: JSON content or reponse dict with error.
    '''
    header, content = raw_content.split(',')
    temp = header.split('/')[-1].split(';')[0]
    if temp != 'json':
        msg = f'File header is not JSON. Header: {header}.'
        raise ValueError(msg)

    output = base64.b64decode(content).decode('utf-8')
    return json.loads(output)


def error_to_response(error):
    '''
    Convenience function for formatting a given exception as a Flask Response.

    Args:
        error (Exception): Error to be formatted.

    Returns:
        flask.Response: Flask response.
    '''
    args = ['    ' + str(x) for x in error.args]
    args = '\n'.join(args)
    klass = error.__class__.__name__
    msg = f'{klass}(\n{args}\n)'
    return flask.Response(
        response=json.dumps(dict(
            error=error.__class__.__name__,
            args=list(map(str, error.args)),
            message=msg,
            code=500,
        )),
        mimetype='application/json',
        status=500,
    )


# SETUP-------------------------------------------------------------------------
def setup_hidebound_directory(target='/mnt/storage'):
    '''
    Creates /mnt/storage/hidebound and /mnt/storage/hidebound/specifications
    directories. Writes a default hidebound config to
    /mnt/storage/hidebound/hidebound_config.json if one does not exist.

    Args:
        target (str, optional): For testing only. Do not call with argument.
            Default: "/mnt/storage".
    '''
    target = Path(target, 'hidebound')
    os.makedirs(target, exist_ok=True)
    os.makedirs(Path(target, 'specifications'), exist_ok=True)

    config = {
        'root_directory': '/mnt/storage/projects',
        'hidebound_directory': '/mnt/storage/hidebound',
        'specification_files': [],
        'include_regex': '',
        'exclude_regex': r'\.DS_Store',
        'write_mode': 'copy'
    }
    config = json.dumps(config, indent=4, sort_keys=True)

    target = Path(target, 'hidebound_config.json')
    if not target.is_file():
        with open(target, 'w') as f:
            f.write(config)


def get_startup_parameters():
    '''
    Gets debug_mode and in initial configuration values. Also sets up hidebound
    directory.

    Returns:
        list: Debug mode bool, configuration dict and filepath.
    '''
    # TODO: Find a way to test this.
    debug = 'DEBUG_MODE' in os.environ.keys()
    config_path = '/mnt/storage/hidebound/hidebound_config.json'
    if debug:
        config_path = '/root/hidebound/resources/test_config.json'
        setup_hidebound_directory('/tmp')
    else:
        setup_hidebound_directory()

    with open(config_path) as f:
        config = json.load(f)
    return debug, config, config_path


# ERRORS------------------------------------------------------------------------
def get_config_error():
    '''
    Convenience function for returning a config error response.

    Returns:
        Response: Config error.
    '''
    msg = 'Please supply a config dictionary.'
    error = TypeError(msg)
    return error_to_response(error)


def get_initialization_error():
    '''
    Convenience function for returning a initialization error response.

    Returns:
        Response: Initialization error.
    '''
    msg = 'Database not initialized. Please call initialize.'
    error = RuntimeError(msg)
    return error_to_response(error)


def get_update_error():
    '''
    Convenience function for returning a update error response.

    Returns:
        Response: Update error.
    '''
    msg = 'Database not updated. Please call update.'
    error = RuntimeError(msg)
    return error_to_response(error)


def get_read_error():
    '''
    Convenience function for returning a read error response.

    Returns:
        Response: Update error.
    '''
    msg = 'Please supply valid read params in the form '
    msg += '{"group_by_asset": BOOL}.'
    error = ValueError(msg)
    return error_to_response(error)


def get_search_error():
    '''
    Convenience function for returning a search error response.

    Returns:
        Response: Update error.
    '''
    msg = 'Please supply valid search params in the form '
    msg += '{"query": SQL query, "group_by_asset": BOOL}.'
    error = ValueError(msg)
    return error_to_response(error)
