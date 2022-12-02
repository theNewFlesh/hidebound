from typing import Any, Dict, Optional, Union

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from pprint import pformat
import base64
import json
import os
import re
import traceback

from flask.testing import FlaskClient
import flask
import jinja2
import lunchbox.tools as lbt
import requests
import rolling_pin.blob_etl as rpb
import yaml

import hidebound.core.logging as hblog
# ------------------------------------------------------------------------------


HOST = '0.0.0.0'
PORT = 8080


@dataclass
class EndPoints:
    '''
    A convenience class for API endpoints.
    '''
    host = HOST
    port = PORT
    api = f'http://{HOST}:{PORT}/api'
    init = f'http://{HOST}:{PORT}/api/initialize'
    update = f'http://{HOST}:{PORT}/api/update'
    create = f'http://{HOST}:{PORT}/api/create'
    export = f'http://{HOST}:{PORT}/api/export'
    delete = f'http://{HOST}:{PORT}/api/delete'
    read = f'http://{HOST}:{PORT}/api/read'
    search = f'http://{HOST}:{PORT}/api/search'
    workflow = f'http://{HOST}:{PORT}/api/workflow'
    progress = f'http://{HOST}:{PORT}/api/progress'
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
    if os.environ.get('REPO_ENV', 'False').lower() == 'true':
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
def setup_hidebound_directories(root):
    # type: (Union[str, Path]) -> None
    '''
    Creates [root]/ingress, [root]/hidebound and [root]/archive directories.

    Args:
        root (str or Path): Root directory.
    '''
    for folder in ['ingress', 'hidebound', 'archive']:
        os.makedirs(Path(root, folder), exist_ok=True)


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


def get_connection_error():
    # type: () -> flask.Response
    '''
    Convenience function for returning a database connection error response.

    Returns:
        Response: Connection error.
    '''
    msg = 'Database not connected.'
    error = RuntimeError(msg)
    return error_to_response(error)


# DASH-TOOLS--------------------------------------------------------------------
def get_progress(logpath=hblog.PROGRESS_LOG_PATH):
    # type: (Union[str, Path]) -> dict
    '''
    Gets current progress state.

    Args:
        logpath (str or Path, optional): Filepath of progress log.
            Default: PROGRESS_LOG_PATH.

    Returns:
        dict: Progess.
    '''
    state = dict(progress=1.0, message='unknown state')
    state.update(hblog.get_progress(logpath))
    return state


def request(store, url, params=None, client=requests):
    # type: (dict, str, Optional[dict], Any) -> dict
    '''
    Execute search against database and update store with response.
    Sets store['content'] to response if there is an error.

    Args:
        store (dict): Dash store.
        url (str): API endpoint.
        params (dict, optional): Request paramaters. Default: None.
        client (object, optional): Client. Default: requests module.

    Returns:
        dict: Store.
    '''
    params_ = None
    if params is not None:
        params_ = json.dumps(params)
    response = client.post(url, json=params_)
    code = response.status_code
    if isinstance(client, FlaskClient):
        response = response.json
    else:
        response = response.json()  # pragma: no cover
    if code < 200 or code >= 300:
        store['content'] = response
    store['ready'] = True
    return response


def search(store, query, group_by_asset, client=requests):
    # type: (dict, str, bool, Any) -> dict
    '''
    Execute search against database and update given store with response.

    Args:
        store (dict): Dash store.
        query (str): Query string.
        group_by_asset (bool): Whether to group the search by asset.
        client (object, optional): Client. Default: requests module.

    Returns:
        dict: Store.
    '''
    params = dict(query=query, group_by_asset=group_by_asset)
    store['content'] = request(store, EndPoints().search, params, client)
    store['query'] = query
    store['ready'] = True
    return store


def format_config(
    config, redact_regex='(_key|_id|_token|url)$', redact_hash=False
):
    # type: (Dict[str, Any], str, bool) -> OrderedDict[str, Any]
    '''
    Redacts credentials of config and formats it for display in component.

    Args:
        config (dict): Configuration dictionary.
        redact_regex (str, optional): Regular expression that matches keys,
            whose values are to be redacted. Default: "(_key|_id|_token|url)$".
        redact_hash (bool, optional): Whether to redact values with the string
            "REDACTED" or a hash of the value. Default: False.

    Returns:
        OrderedDict: Formatted config.
    '''
    def redact(key, value, as_hash):
        if as_hash:
            return 'hash-' + str(hash(value)).lstrip('-')
        return 'REDACTED'

    def predicate(key, value):
        if re.search(redact_regex, key):
            return True
        return False

    config = rpb.BlobETL(config) \
        .set(predicate, value_setter=lambda k, v: redact(k, v, redact_hash)) \
        .to_dict()
    output = OrderedDict()
    keys = [
        'ingress_directory',
        'staging_directory',
        'include_regex',
        'exclude_regex',
        'write_mode',
        'redact_regex',
        'redact_hash',
        'specification_files',
        'workflow',
        'dask',
        'exporters',
        'webhooks',
    ]
    all_ = set(config.keys())
    cross = all_.intersection(keys)
    diff = sorted(list(all_.difference(cross)))
    keys = list(filter(lambda x: x in cross, keys)) + diff
    for key in keys:
        val = re.sub(r'\.\.\.$', '', yaml.safe_dump(config[key])).rstrip('\n')
        output[key] = val
    return output
