from typing import Any

from json import JSONDecodeError
import json

import numpy as np
import flask
import flasgger as swg
from schematics.exceptions import DataError, ValidationError
from werkzeug.exceptions import BadRequest

from hidebound.core.database import Database
import hidebound.core.logging as hblog
import hidebound.core.validators as vd
import hidebound.server.extensions as ext
import hidebound.server.server_tools as hst
# ------------------------------------------------------------------------------


'''
Hidebound service API.
'''


API = flask.Blueprint('hidebound_api', __name__, url_prefix='')


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


@API.route('/api/initialize', methods=['POST'])
@swg.swag_from(dict(
    parameters=[
        dict(
            name='config',
            type='dict',
            description='Hidebound configuration.',
            required=True,
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
    try:
        config = flask.request.get_json()  # type: Any
        config = json.loads(config)
    except (BadRequest, JSONDecodeError, TypeError):
        return hst.get_config_error()
    if not isinstance(config, dict):
        return hst.get_config_error()

    ext.hidebound.database = Database.from_config(config)

    return flask.Response(
        response=json.dumps(dict(message='Database initialized.')),
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
    try:
        ext.hidebound.database.create()
    except RuntimeError:
        return hst.get_update_error()

    return flask.Response(
        response=json.dumps(dict(message='Hidebound data created.')),
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
    params = flask.request.get_json()  # type: Any
    group_by_asset = False
    if params not in [None, {}]:
        try:
            params = json.loads(params)
            group_by_asset = params['group_by_asset']
            assert isinstance(group_by_asset, bool)
        except (JSONDecodeError, TypeError, KeyError, AssertionError):
            return hst.get_read_error()

    response = {}  # type: Any
    try:
        response = ext.hidebound.database.read(group_by_asset=group_by_asset)
    except Exception as error:
        if isinstance(error, RuntimeError):
            return hst.get_update_error()
        return hst.error_to_response(error)

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
    ext.hidebound.database.update()
    return flask.Response(
        response=json.dumps(dict(message='Database updated.')),
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
    ext.hidebound.database.delete()
    return flask.Response(
        response=json.dumps(dict(message='Hidebound data deleted.')),
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
    try:
        ext.hidebound.database.export()
    except Exception as error:
        return hst.error_to_response(error)

    return flask.Response(
        response=json.dumps(dict(message='Hidebound data exported.')),
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
    params = flask.request.get_json()  # type: Any
    group_by_asset = False
    try:
        params = json.loads(params)
        query = params['query']
        if 'group_by_asset' in params.keys():
            group_by_asset = params['group_by_asset']
            assert isinstance(group_by_asset, bool)
    except (JSONDecodeError, TypeError, KeyError, AssertionError):
        return hst.get_search_error()

    if ext.hidebound.database.data is None:
        return hst.get_update_error()

    response = None
    try:
        response = ext.hidebound.database \
            .search(query, group_by_asset=group_by_asset)
    except Exception as e:
        return hst.error_to_response(e)

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
            name='steps',
            type='list',
            description='Ordered list of API calls.',
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
    params = flask.request.get_json()  # type: Any
    params = json.loads(params)
    steps = params['steps']

    # get and validate workflow steps
    try:
        vd.is_workflow(steps)
    except ValidationError as e:
        return hst.error_to_response(e)

    # run through workflow
    for step in steps:
        try:
            getattr(ext.hidebound.database, step)()
        except Exception as error:  # pragma: no cover
            return hst.error_to_response(error)  # pragma: no cover

    return flask.Response(
        response=json.dumps(dict(
            message='Workflow completed.', steps=steps)),
        mimetype='application/json'
    )


@API.route('/api/progress', methods=['GET', 'POST'])
@swg.swag_from(dict(
    parameters=[],
    responses={
        200: dict(
            description='Current progress of Hidebound.',
            content='application/json',
        ),
        500: dict(
            description='Internal server error.',
        )
    }
))
def progress():
    # type: () -> flask.Response
    '''
    Get hidebound app progress.

    Returns:
        Response: Flask Response instance.
    '''
    return flask.Response(
        response=json.dumps(hblog.get_progress()),
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
    return hst.error_to_response(error)


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
    return hst.error_to_response(error)


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
    return hst.error_to_response(error)


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
    return hst.error_to_response(error)
# ------------------------------------------------------------------------------


API.register_error_handler(500, handle_data_error)
API.register_error_handler(500, handle_key_error)
API.register_error_handler(500, handle_type_error)
API.register_error_handler(500, handle_json_decode_error)
