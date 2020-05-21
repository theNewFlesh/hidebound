from json import JSONDecodeError
import json

import flasgger as swg
import flask
import numpy as np
from schematics.exceptions import DataError

from hidebound.core.database import Database
import hidebound.server.server_tools as server_tools
# ------------------------------------------------------------------------------


'''
Hidebound service API.
'''


API = flask.Blueprint('api', __name__, url_prefix='')
# TODO: Find a way to share database and config inside Flask instance without globals.
DATABASE = None
CONFIG = None


@API.route('/api')
def api():
    '''
    Route to Hidebound API documentation.

    Returns:
        html: Flassger generated API page.
    '''
    # TODO: Test this with selenium.
    return flask.redirect(flask.url_for('flasgger.apidocs'))


@API.route('/api/initialize', methods=['POST'])
@swg.swag_from(dict(
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
    global DATABASE
    global CONFIG

    config = dict(
        specification_files=[],
        include_regex='',
        exclude_regex=r'\.DS_Store',
        write_mode='copy',
    )

    temp = flask.request.get_json()
    try:
        temp = json.loads(temp)
    except (JSONDecodeError, TypeError):
        return server_tools.get_config_error()
    if not isinstance(temp, dict):
        return server_tools.get_config_error()

    config.update(temp)
    DATABASE = Database.from_config(config)
    CONFIG = config

    return flask.Response(
        response=json.dumps(dict(
            message='Database initialized.',
            config=config,
        )),
        mimetype='application/json'
    )


@API.route('/api/update', methods=['POST'])
@swg.swag_from(dict(
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
    global DATABASE
    global CONFIG

    if DATABASE is None:
        return server_tools.get_initialization_error()

    DATABASE.update()
    return flask.Response(
        response=json.dumps(dict(
            message='Database updated.',
            config=CONFIG,
        )),
        mimetype='application/json'
    )


@API.route('/api/read', methods=['GET', 'POST'])
@swg.swag_from(dict(
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
    global DATABASE
    global CONFIG

    if DATABASE is None:
        return server_tools.get_initialization_error()

    params = flask.request.get_json()
    grp = False
    if params is not None:
        try:
            params = json.loads(params)
            grp = params['group_by_asset']
            assert(isinstance(grp, bool))
        except (JSONDecodeError, TypeError, KeyError, AssertionError):
            return server_tools.get_read_error()

    response = {}
    try:
        response = DATABASE.read(group_by_asset=grp)
    except Exception as error:
        if isinstance(error, RuntimeError):
            return server_tools.get_update_error()
        return server_tools.error_to_response(error)

    response = response.replace({np.nan: None}).to_dict(orient='records')
    response = {'response': response}
    return flask.Response(
        response=json.dumps(response),
        mimetype='application/json'
    )


@API.route('/api/search', methods=['POST'])
@swg.swag_from(dict(
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
    global DATABASE
    global CONFIG

    params = flask.request.get_json()
    grp = False
    try:
        params = json.loads(params)
        query = params['query']
        if 'group_by_asset' in params.keys():
            grp = params['group_by_asset']
            assert(isinstance(grp, bool))
    except (JSONDecodeError, TypeError, KeyError, AssertionError):
        return server_tools.get_search_error()

    if DATABASE is None:
        return server_tools.get_initialization_error()

    if DATABASE.data is None:
        return server_tools.get_update_error()

    response = None
    try:
        response = DATABASE.search(query, group_by_asset=grp)
    except Exception as e:
        return server_tools.error_to_response(e)

    response.asset_valid = response.asset_valid.astype(bool)
    response = response.replace({np.nan: None}).to_dict(orient='records')
    response = {'response': response}
    return flask.Response(
        response=json.dumps(response),
        mimetype='application/json'
    )


@API.route('/api/create', methods=['POST'])
@swg.swag_from(dict(
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
    global DATABASE
    global CONFIG

    if DATABASE is None:
        return server_tools.get_initialization_error()

    try:
        DATABASE.create()
    except RuntimeError:
        return server_tools.get_update_error()

    return flask.Response(
        response=json.dumps(dict(
            message='Hidebound data created.',
            config=CONFIG,
        )),
        mimetype='application/json'
    )


@API.route('/api/delete', methods=['POST'])
@swg.swag_from(dict(
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
    global DATABASE
    global CONFIG

    if DATABASE is None:
        return server_tools.get_initialization_error()

    DATABASE.delete()
    return flask.Response(
        response=json.dumps(dict(
            message='Hidebound data deleted.',
            config=CONFIG,
        )),
        mimetype='application/json'
    )


@API.errorhandler(DataError)
def handle_data_error(error):
    '''
    Handles errors raise by config validation.

    Args:
        error (DataError): Config validation error.

    Returns:
        Response: DataError response.
    '''
    return server_tools.error_to_response(error)
# ------------------------------------------------------------------------------


API.register_error_handler(500, handle_data_error)
