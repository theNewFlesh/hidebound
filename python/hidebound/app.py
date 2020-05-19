import base64
from json import JSONDecodeError
import json
import os
from pathlib import Path

import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from flasgger import swag_from
from flask import Response, request, redirect, url_for
from schematics.exceptions import DataError
import numpy as np

from hidebound.database import Database
import hidebound.components as components
# ------------------------------------------------------------------------------


'''
Hidebound service used for displaying and interacting with Hidebound database.
'''


APP = components.get_app()


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


@APP.server.route('/static/<stylesheet>')
def serve_stylesheet(stylesheet):
    '''
    Serve stylesheet to app.

    Args:
        stylesheet (str): stylesheet filename.

    Returns:
        flask.Response: Response.
    '''
    params = dict(
        COLOR_SCHEME=components.COLOR_SCHEME,
        FONT_FAMILY=components.FONT_FAMILY,
    )
    content = components.render_template(stylesheet + '.j2', params)
    return Response(content, mimetype='text/css')


# EVENTS------------------------------------------------------------------------
# TODO: Find a way to test events.
@APP.callback(
    Output('store', 'data'),
    [
        Input('init-button', 'n_clicks'),
        Input('update-button', 'n_clicks'),
        Input('create-button', 'n_clicks'),
        Input('delete-button', 'n_clicks'),
        Input('search-button', 'n_clicks'),
        Input('dropdown', 'value'),
        Input('query', 'value'),
        Input('upload', 'contents'),
        Input('validate-button', 'n_clicks'),
        Input('write-button', 'n_clicks'),
    ],
    [State('store', 'data')]
)
def on_event(*inputs):
    '''
    Update Hidebound database instance, and updates store with input data.

    Args:
        inputs (tuple): Input elements.

    Returns:
        dict: Store data.
    '''
    store = inputs[-1] or {}
    config = store.get('config', APP.server._config)

    context = dash.callback_context
    inputs = {}
    for item in context.inputs_list:
        key = item['id']
        val = None
        if 'value' in item.keys():
            val = item['value']
        inputs[key] = val

    # convert search dropdown to boolean
    grp = False
    if inputs['dropdown'] == 'asset':
        grp = True
    inputs['dropdown'] = grp

    input_id = context.triggered[0]['prop_id'].split('.')[0]

    if input_id == 'init-button':
        APP.server._database = Database.from_config(config)

    elif input_id == 'update-button':
        if APP.server._database is None:
            APP.server._database = Database.from_config(config)
        APP.server._database.update()
        params = json.dumps({'group_by_asset': grp})
        response = APP.server.test_client().post('/api/read', json=params).json
        store['/api/read'] = response

    elif input_id == 'create-button':
        APP.server._database.create()

    elif input_id == 'delete-button':
        APP.server._database.delete()

    elif input_id == 'search-button':
        query = json.dumps({
            'query': inputs['query'],
            'group_by_asset': inputs['dropdown']
        })
        response = APP.server.test_client().post('/api/search', json=query).json
        store['/api/read'] = response

    elif input_id == 'upload':
        try:
            store['config'] = parse_json_file_content(inputs['upload'])
        except Exception as error:
            store['config'] = error_to_response(error).json

    elif input_id == 'validate-button':
        pass

    elif input_id == 'write-button':
        pass

    return store


@APP.callback(
    Output('table-content', 'children'),
    [Input('store', 'data')]
)
def on_datatable_update(store):
    '''
    Updates datatable with read information from store.

    Args:
        store (dict): Store data.

    Returns:
        DataTable: Dash DataTable.
    '''
    if store in [{}, None]:
        raise PreventUpdate
    data = store.get('/api/read', None)
    if data is None:
        raise PreventUpdate

    if 'error' in data.keys():
        return json.dumps(data, indent=4, sort_keys=True)
    return components.get_datatable(data['response'])


@APP.callback(
    Output('content', 'children'),
    [Input('tabs', 'value')],
    [State('store', 'data')]
)
def on_get_tab(tab, store):
    '''
    Serve content for app tabs.

    Args:
        tab (str): Name of tab to render.
        store (dict): Store.

    Returns:
        flask.Response: Response.
    '''
    if tab == 'data':
        return components.get_data_tab()
    elif tab == 'config':
        store = store or {}
        config = store.get('config', APP.server._config)
        return components.get_config_tab(config)


@APP.callback(
    Output('json-editor-row', 'children'),
    [Input('store', 'data')]
)
def on_json_editor_update(store):
    '''
    Updates JSON editor with config information from store.

    Args:
        store (dict): Store data.

    Returns:
        flask.Response: Response.
    '''
    if store in [{}, None]:
        raise PreventUpdate
    config = store.get('config', None)
    if config is None:
        raise PreventUpdate
    return components.get_json_editor(config)


# API---------------------------------------------------------------------------
@APP.server.route('/api')
def api():
    '''
    Route to Hidebound API documentation.

    Returns:
        html: Flassger generated API page.
    '''
    return redirect(url_for('flasgger.apidocs'))


@APP.server.route('/api/initialize', methods=['POST'])
@swag_from(dict(
    parameters=[
        dict(
            name='root_directory',
            type='string',
            description='Root directory to recurse.',
            required=True,
            default='',
        ),
        dict(
            name='hidebound_directory',
            type='string',
            description='Directory where hidebound directory will be created and hidebound data saved.',  # noqa E501
            required=True,
            default='',
        ),
        dict(
            name='specification_files',
            type='list',
            description='List of asset specification files.',
            required=False,
            default='',
        ),
        dict(
            name='include_regex',
            type='string',
            description='Include filenames that match this regex.',
            required=False,
            default='',
        ),
        dict(
            name='exclude_regex',
            type='string',
            description='Exclude filenames that match this regex.',
            required=False,
            default=r'\.DS_Store',
        ),
        dict(
            name='write_mode',
            type='string',
            description='How assets will be extracted to hidebound/data directory.',
            required=False,
            default='copy',
            enum=['copy', 'move'],
        )
    ],
    responses={
        200: dict(
            description='Hidebound database successfully initialized.',
            content='application/json',
        ),
        400: dict(
            description='Invalid configuration.',
            example=dict(
                error='''
DataError(
    {'write_mode': ValidationError([ErrorMessage("foo is not in ['copy', 'move'].", None)])}
)'''[1:],
                success=False,
            )
        )
    }
))
def initialize():
    '''
    Initialize database with given config.

    Returns:
        Response: Flask Response instance.
    '''
    config = dict(
        specification_files=[],
        include_regex='',
        exclude_regex=r'\.DS_Store',
        write_mode='copy',
    )

    temp = request.get_json()
    try:
        temp = json.loads(temp)
    except (JSONDecodeError, TypeError):
        return get_config_error()
    if not isinstance(temp, dict):
        return get_config_error()

    config.update(temp)
    APP.server._database = Database.from_config(config)
    APP.server._config = config

    return Response(
        response=json.dumps(dict(
            message='Database initialized.',
            config=config,
        )),
        mimetype='application/json'
    )


@APP.server.route('/api/update', methods=['POST'])
@swag_from(dict(
    parameters=[],
    responses={
        200: dict(
            description='Hidebound database successfully updated.',
            content='application/json',
        ),
        500: dict(
            description='Internal server error.',
        )
    }
))
def update():
    '''
    Update database.

    Returns:
        Response: Flask Response instance.
    '''
    if APP.server._database is None:
        return get_initialization_error()

    APP.server._database.update()
    return Response(
        response=json.dumps(dict(
            message='Database updated.',
            config=APP.server._config,
        )),
        mimetype='application/json'
    )


@APP.server.route('/api/read', methods=['GET', 'POST'])
@swag_from(dict(
    parameters=[
        dict(
            name='group_by_asset',
            type='bool',
            description='Whether to group resulting data by asset.',
            required=False,
            default=False,
        ),
    ],
    responses={
        200: dict(
            description='Read all data from database.',
            content='application/json',
        ),
        500: dict(
            description='Internal server error.',
        )
    }
))
def read():
    '''
    Read database.

    Returns:
        Response: Flask Response instance.
    '''
    if APP.server._database is None:
        return get_initialization_error()

    params = request.get_json()
    grp = False
    if params is not None:
        try:
            params = json.loads(params)
            grp = params['group_by_asset']
            assert(isinstance(grp, bool))
        except (JSONDecodeError, TypeError, KeyError, AssertionError):
            return get_read_error()

    response = {}
    try:
        response = APP.server._database.read(group_by_asset=grp)
    except Exception as error:
        if isinstance(error, RuntimeError):
            return get_update_error()
        return error_to_response(error)

    response = response.replace({np.nan: None}).to_dict(orient='records')
    response = {'response': response}
    return Response(
        response=json.dumps(response),
        mimetype='application/json'
    )


@APP.server.route('/api/search', methods=['POST'])
@swag_from(dict(
    parameters=[
        dict(
            name='query',
            type='string',
            description='SQL query for searching database. Make sure to use "FROM data" in query.',
            required=True,
        ),
        dict(
            name='group_by_asset',
            type='bool',
            description='Whether to group resulting search by asset.',
            required=False,
            default=False,
        ),
    ],
    responses={
        200: dict(
            description='Returns a list of JSON compatible dictionaries, one per row.',
            content='application/json',
        ),
        500: dict(
            description='Internal server error.',
        )
    }
))
def search():
    '''
    Search database with a given SQL query.

    Returns:
        Response: Flask Response instance.
    '''
    params = request.get_json()
    grp = False
    try:
        params = json.loads(params)
        query = params['query']
        if 'group_by_asset' in params.keys():
            grp = params['group_by_asset']
            assert(isinstance(grp, bool))
    except (JSONDecodeError, TypeError, KeyError, AssertionError):
        return get_search_error()

    if APP.server._database is None:
        return get_initialization_error()

    if APP.server._database.data is None:
        return get_update_error()

    response = None
    try:
        response = APP.server._database.search(query, group_by_asset=grp)
    except Exception as e:
        return error_to_response(e)

    response = response.replace({np.nan: None}).to_dict(orient='records')
    response = {'response': response}
    return Response(
        response=json.dumps(response),
        mimetype='application/json'
    )


@APP.server.route('/api/create', methods=['POST'])
@swag_from(dict(
    parameters=[],
    responses={
        200: dict(
            description='Hidebound data successfully deleted.',
            content='application/json',
        ),
        500: dict(
            description='Internal server error.',
        )
    }
))
def create():
    '''
    Create hidebound data.

    Returns:
        Response: Flask Response instance.
    '''
    if APP.server._database is None:
        return get_initialization_error()

    try:
        APP.server._database.create()
    except RuntimeError:
        return get_update_error()

    return Response(
        response=json.dumps(dict(
            message='Hidebound data created.',
            config=APP.server._config,
        )),
        mimetype='application/json'
    )


@APP.server.route('/api/delete', methods=['POST'])
@swag_from(dict(
    parameters=[],
    responses={
        200: dict(
            description='Hidebound data successfully deleted.',
            content='application/json',
        ),
        500: dict(
            description='Internal server error.',
        )
    }
))
def delete():
    '''
    Delete hidebound data.

    Returns:
        Response: Flask Response instance.
    '''
    if APP.server._database is None:
        return get_initialization_error()

    APP.server._database.delete()
    return Response(
        response=json.dumps(dict(
            message='Hidebound data deleted.',
            config=APP.server._config,
        )),
        mimetype='application/json'
    )


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


# ERROR-HANDLERS----------------------------------------------------------------
def error_to_response(error):
    '''
    Convenience function for formatting a given exception as a Flask Response.

    Args:
        error (Exception): Error to be formatted.

    Returns:
        Response: Flask response.
    '''
    args = ['    ' + str(x) for x in error.args]
    args = '\n'.join(args)
    klass = error.__class__.__name__
    msg = f'{klass}(\n{args}\n)'
    return Response(
        response=json.dumps(dict(
            error=error.__class__.__name__,
            args=list(map(str, error.args)),
            message=msg,
            code=500,
        )),
        mimetype='application/json',
        status=500,
    )


@APP.server.errorhandler(DataError)
def handle_data_error(error):
    '''
    Handles errors raise by config validation.

    Args:
        error (DataError): Config validation error.

    Returns:
        Response: DataError response.
    '''
    return error_to_response(error)
# ------------------------------------------------------------------------------


APP.server.register_error_handler(500, handle_data_error)


if __name__ == '__main__':
    debug, config, config_path = get_startup_parameters()
    APP.server._config = config
    APP.server._config_path = config_path
    APP.run_server(debug=debug, host='0.0.0.0', port=5000)
