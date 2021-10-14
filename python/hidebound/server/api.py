from typing import Any, Optional, Tuple

from json import JSONDecodeError
import json

import numpy as np
import flask
import flasgger as swg
from schematics.exceptions import DataError

from hidebound.core.database import Database
import hidebound.server.server_tools as server_tools
# ------------------------------------------------------------------------------


'''
Hidebound service API.
'''


API = flask.Blueprint('api', __name__, url_prefix='')
# TODO: Find a way to share database and config inside Flask instance without globals.
DATABASE = None  # type: Any
CONFIG = None  # type: Optional[dict]


@API.route('/api')
def api():
    # type: () -> Any
    '''
    Route to Hidebound API documentation.

    Returns:
        html: Flassger generated API page.
    '''
    # TODO: Test this with selenium.
    return flask.redirect(flask.url_for('flasgger.apidocs'))


def _get_database(config):
    # type: (dict) -> Tuple[Database, dict]
    '''
    Convenience function for creating a database from a given config.

    Args:
        config (dict): Configuration.

    Returns:
        tuple[Database, dict]: Database and config.
    '''
    config_ = dict(
        specification_files=[],
        include_regex='',
        exclude_regex=r'\.DS_Store',
        write_mode='copy',
    )
    config_.update(config)
    return Database.from_config(config_), config_


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
            description='How assets will be extracted to hidebound/content directory.',
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
    # type: () -> flask.Response
    '''
    Initialize database with given config.

    Returns:
        Response: Flask Response instance.
    '''
    global DATABASE
    global CONFIG

    config = flask.request.get_json()  # type: Any
    try:
        config = json.loads(config)
    except (JSONDecodeError, TypeError):
        return server_tools.get_config_error()
    if not isinstance(config, dict):
        return server_tools.get_config_error()

    DATABASE, CONFIG = _get_database(config)
    return flask.Response(
        response=json.dumps(dict(
            message='Database initialized.',
            config=config,
        )),
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
    # type: () -> flask.Response
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
    # type: () -> flask.Response
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

    response = {}  # type: Any
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
    # type: () -> flask.Response
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
    # type: () -> flask.Response
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


@API.route('/api/export', methods=['POST'])
@swg.swag_from(dict(
    parameters=[],
    responses={
        200: dict(
            description='Hidebound data successfully exported.',
            content='application/json',
        ),
        500: dict(
            description='Internal server error.',
        )
    }
))
def export():
    # type: () -> flask.Response
    '''
    Export hidebound data.

    Returns:
        Response: Flask Response instance.
    '''
    global DATABASE
    global CONFIG

    if DATABASE is None:
        return server_tools.get_initialization_error()

    try:
        DATABASE.export()
    except Exception as error:
        return server_tools.error_to_response(error)

    return flask.Response(
        response=json.dumps(dict(
            message='Hidebound data exported.',
            config=CONFIG,
        )),
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
    # type: () -> flask.Response
    '''
    Search database with a given SQL query.

    Returns:
        Response: Flask Response instance.
    '''
    global DATABASE
    global CONFIG

    params = flask.request.get_json()  # type: Any
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


@API.route('/api/workflow', methods=['POST'])
@swg.swag_from(dict(
    parameters=[
        dict(
            name='workflow',
            type='list',
            description='Ordered list of API calls.',
            required=True,
        ),
        dict(
            name='config',
            type='dict',
            description='Hidebound configuration.',
            required=True,
        )
    ],
    responses={
        200: dict(
            description='Hidebound workflow ran successfully.',
            content='application/json',
        ),
        500: dict(
            description='Internal server error.',
        )
    }
))
def workflow():
    # type: () -> flask.Response
    '''
    Run given hidebound workflow.

    Returns:
        Response: Flask Response instance.
    '''
    global DATABASE
    global CONFIG

    params = flask.request.get_json()  # type: Any
    params = json.loads(params)
    workflow = params['workflow']
    config = params['config']

    # get and validate workflow steps
    legal = ['update', 'create', 'export', 'delete']
    diff = sorted(list(set(workflow).difference(legal)))
    if len(diff) > 0:
        msg = f'Found illegal workflow steps: {diff}. Legal steps: {legal}.'
        return server_tools.error_to_response(ValueError(msg))

    # run through workflow
    DATABASE, CONFIG = _get_database(config)
    for step in workflow:
        try:
            getattr(DATABASE, step)()
        except Exception as error:  # pragma: no cover
            return server_tools.error_to_response(error)  # pragma: no cover

    return flask.Response(
        response=json.dumps(dict(
            message='Workflow completed.',
            workflow=workflow,
            config=CONFIG,
        )),
        mimetype='application/json'
    )


@API.errorhandler(DataError)
def handle_data_error(error):
    # type: (DataError) -> flask.Response
    '''
    Handles errors raise by config validation.

    Args:
        error (DataError): Config validation error.

    Returns:
        Response: DataError response.
    '''
    return server_tools.error_to_response(error)


@API.errorhandler(KeyError)
def handle_key_error(error):
    # type: (KeyError) -> flask.Response
    '''
    Handles key errors.

    Args:
        error (KeyError): Key error.

    Returns:
        Response: KeyError response.
    '''
    return server_tools.error_to_response(error)


@API.errorhandler(TypeError)
def handle_type_error(error):
    # type: (TypeError) -> flask.Response
    '''
    Handles key errors.

    Args:
        error (TypeError): Key error.

    Returns:
        Response: TypeError response.
    '''
    return server_tools.error_to_response(error)


@API.errorhandler(JSONDecodeError)
def handle_json_decode_error(error):
    # type: (JSONDecodeError) -> flask.Response
    '''
    Handles key errors.

    Args:
        error (JSONDecodeError): Key error.

    Returns:
        Response: JSONDecodeError response.
    '''
    return server_tools.error_to_response(error)
# ------------------------------------------------------------------------------


API.register_error_handler(500, handle_data_error)
API.register_error_handler(500, handle_key_error)
API.register_error_handler(500, handle_type_error)
API.register_error_handler(500, handle_json_decode_error)
