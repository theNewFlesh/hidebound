from copy import copy
from json import JSONDecodeError
import json
import os
from pathlib import Path

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
@APP.callback(Output('content', 'children'), [Input('tabs', 'value')])
def on_get_tab(tab):
    '''
    Serve content for app tabs.

    Args:
        tab (str): Name of tab to render.

    Returns:
        flask.Response: Response.
    '''
    if tab == 'data':
        return components.get_data_tab()
    elif tab == 'config':
        return components.get_config_tab(APP.server._config)


@APP.callback(
    Output('content', 'data-init-button'), [Input('init-button', 'n_clicks')]
)
def on_init_button_click(n_clicks):
    '''
    Updates the Database with the current config.

    Args:
        n_clicks (int): Number of button clicks.

    Returns:
        flask.Response: Response.
    '''
    if n_clicks is not None:
        APP.server._database = Database.from_json(APP.server._config_path)


@APP.callback(
    Output('session-store', 'data'),
    [Input('update-button', 'n_clicks')],
    [State('session-store', 'data')]
)
def on_update_button_click(n_clicks, data):
    '''
    Updates the Database with the current config.

    Args:
        n_clicks (int): Number of button clicks.

    Returns:
        flask.Response: Response.
    '''
    if n_clicks is None:
        raise PreventUpdate

    if APP.server._database is None:
        APP.server._database = Database.from_json(APP.server._config_path)
    APP.server._database.update()
    data = APP.server.test_client().get('/api/read').json
    return {'read': data}


@APP.callback(
    Output('table-content', 'children'),
    [Input('session-store', 'modified_timestamp')],
    [State('session-store', 'data')]
)
def on_session_data_update(timestamp, data):
    '''
    Updates the datatable with session data.

    Args:
        timestamp (int): Session timestamp.
        data (dict): Session data.

    Returns:
        flask.Response: Response.
    '''
    if timestamp is None:
        raise PreventUpdate
    data = data or {'read': {'response': []}}
    data = data['read']['response']
    return components.get_datatable(data)


@APP.callback(
    Output('content', 'data-create-button'), [Input('create-button', 'n_clicks')]
)
def on_create_button_click(n_clicks):
    '''
    Writes data to hidebound/data and hidebound/metadata.

    Args:
        n_clicks (int): Number of button clicks.

    Returns:
        flask.Response: Response.
    '''
    if n_clicks is not None:
        APP.server._database.create()


@APP.callback(
    Output('content', 'data-delete-button'), [Input('delete-button', 'n_clicks')]
)
def on_delete_button_click(n_clicks):
    '''
    Deletes all data in hidebound/data and hidebound/metadata.

    Args:
        n_clicks (int): Number of button clicks.

    Returns:
        flask.Response: Response.
    '''
    if n_clicks is not None:
        APP.server._database.delete()


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

    config = copy(config)
    config['specifications'] = [x.__name__.lower() for x in config['specifications']]
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
    parameters=[],
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
    # TODO: add group_by_asset support
    if APP.server._database is None:
        return get_initialization_error()

    response = {}
    try:
        response = APP.server._database.read()
    except RuntimeError:
        return get_update_error()

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
        )
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
    query = request.get_json()
    try:
        query = json.loads(query)['query']
    except (JSONDecodeError, TypeError, KeyError):
        return get_query_error()

    # TODO: add group_by_asset support
    if APP.server._database is None:
        return get_initialization_error()

    if APP.server._database.data is None:
        return get_update_error()

    response = None
    try:
        response = APP.server._database.search(query)
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


def get_query_error():
    '''
    Convenience function for returning a query error response.

    Returns:
        Response: Query error.
    '''
    msg = 'Please supply a valid query of the form {"query": SQL}.'
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
