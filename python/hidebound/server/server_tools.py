from typing import Any, Dict, Tuple, Union

from pathlib import Path
from pprint import pformat
import base64
import json
import os
import traceback

import flask
import jinja2
import jsoncomment as jsonc
import lunchbox.tools as lbt
# ------------------------------------------------------------------------------


def render_template(filename, parameters):
    # type: (str, Dict[str, Any]) -> bytes
    '''
    Renders a jinja2 template given by filename with given parameters.

    Args:
        filename (str): Filename of template.
        parameters (dict): Dictionary of template parameters.

    Returns:
        bytes: HTML.
    '''
    # path to templates inside pip package
    tempdir = lbt.relative_path(__file__, '../templates').as_posix()

    # path to templates inside repo
    if 'REPO_ENV' in os.environ.keys():
        tempdir = lbt.relative_path(__file__, '../../../templates').as_posix()

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(tempdir),
        keep_trailing_newline=True
    )
    output = env.get_template(filename).render(parameters).encode('utf-8')
    return output


def parse_json_file_content(raw_content):
    # type: (bytes) -> Dict
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
    header, content = raw_content.split(',')  # type: ignore
    temp = header.split('/')[-1].split(';')[0]  # type: ignore
    if temp != 'json':
        msg = f'File header is not JSON. Header: {header}.'  # type: ignore
        raise ValueError(msg)

    output = base64.b64decode(content).decode('utf-8')
    return json.loads(output)


def error_to_response(error):
    # type: (Exception) -> flask.Response
    '''
    Convenience function for formatting a given exception as a Flask Response.

    Args:
        error (Exception): Error to be formatted.

    Returns:
        flask.Response: Flask response.
    '''
    args = []  # type: Any
    for arg in error.args:
        if hasattr(arg, 'items'):
            for key, val in arg.items():
                args.append(pformat({key: pformat(val)}))
        else:
            args.append(str(arg))
    args = ['    ' + x for x in args]
    args = '\n'.join(args)
    klass = error.__class__.__name__
    msg = f'{klass}(\n{args}\n)'
    return flask.Response(
        response=json.dumps(dict(
            error=error.__class__.__name__,
            args=list(map(str, error.args)),
            message=msg,
            code=500,
            traceback=traceback.format_exc(),
        )),
        mimetype='application/json',
        status=500,
    )


# SETUP-------------------------------------------------------------------------
def setup_hidebound_directory(root, config_path=None):
    # type: (Union[str, Path], Union[str, Path, None]) -> Tuple[Dict, str]
    '''
    Creates [root]/hidebound and [root]/hidebound/config directories.
    Writes a default hidebound config to
    [root]/hidebound/config/hidebound_config.json if one does not exist.

    Args:
        root (str or Path): Root directory of hidebound data.
        config_path (str or Path, optional): Filepath of config data to be
            written to [root]/hidebound/config/hidebound_config.json.
            Default: None.

    Return:
        tuple[dict, str]: Config data and filepath.
    '''
    root = Path(root)
    hb_root = Path(root, 'hidebound').as_posix()
    config_dir = Path(hb_root, 'config')
    os.makedirs(config_dir, exist_ok=True)
    target = Path(config_dir, 'hidebound_config.json').as_posix()

    config = {
        'root_directory': Path(root, 'projects').as_posix(),
        'hidebound_directory': hb_root,
        'specification_files': [],
        'include_regex': '',
        'exclude_regex': r'\.DS_Store',
        'write_mode': 'copy'
    }
    if config_path is not None:
        with open(config_path) as f:
            config = jsonc.JsonComment().load(f)

    with open(target, 'w') as f:
        json.dump(config, f, indent=4, sort_keys=True)

    return config, target


# ERRORS------------------------------------------------------------------------
def get_config_error():
    # type: () -> flask.Response
    '''
    Convenience function for returning a config error response.

    Returns:
        Response: Config error.
    '''
    msg = 'Please supply a config dictionary.'
    error = TypeError(msg)
    return error_to_response(error)


def get_initialization_error():
    # type: () -> flask.Response
    '''
    Convenience function for returning a initialization error response.

    Returns:
        Response: Initialization error.
    '''
    msg = 'Database not initialized. Please call initialize.'
    error = RuntimeError(msg)
    return error_to_response(error)


def get_update_error():
    # type: () -> flask.Response
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
    # type: () -> flask.Response
    '''
    Convenience function for returning a search error response.

    Returns:
        Response: Update error.
    '''
    msg = 'Please supply valid search params in the form '
    msg += '{"query": SQL query, "group_by_asset": BOOL}.'
    error = ValueError(msg)
    return error_to_response(error)
