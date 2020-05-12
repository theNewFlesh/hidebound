from copy import copy
import json

from flask import Flask, Response, request, redirect, url_for
from flasgger import Swagger, swag_from
import numpy as np
from schematics.exceptions import DataError

from hidebound.database import Database
# ------------------------------------------------------------------------------


'''
Hidebound service used for displaying and interacting with Hidebound database.
'''


app = Flask(__name__)
swagger = Swagger(app)
app._database = None
app._config = None


# API---------------------------------------------------------------------------
@app.route('/api')
def api():
    '''
    Route to Hidebound API documentation.

    Returns:
        html: Flassger generated API page.
    '''
    return redirect(url_for('flasgger.apidocs'))  # pragma: no cover


@app.route('/api/initialize', methods=['POST'])
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
            name='hidebound_parent_directory',
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

    # ensure valid json
    msg = 'Please supply a config dictionary.'
    error = TypeError(msg)
    error = error_to_response(error)

    temp = request.get_json()
    try:
        temp = json.loads(temp)
    except TypeError:
        return error
    if not isinstance(temp, dict):
        return error

    config.update(temp)
    app._database = Database.from_config(config)

    config = copy(config)
    config['specifications'] = [x.__name__.lower() for x in config['specifications']]
    app._config = config
    return Response(
        response=json.dumps(dict(
            message='Database initialized.',
            config=config,
        )),
        mimetype='application/json'
    )


@app.route('/api/update', methods=['POST'])
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
    if app._database is None:
        msg = 'Database not initialized. Please call initialize.'
        error = RuntimeError(msg)
        return error_to_response(error)

    app._database.update()
    return Response(
        response=json.dumps(dict(
            message='Database updated.',
            config=app._config,
        )),
        mimetype='application/json'
    )


@app.route('/api/read', methods=['GET', 'POST'])
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
    if app._database is None:
        msg = 'Database not initialized. Please call initialize.'
        error = RuntimeError(msg)
        return error_to_response(error)

    response = {}
    try:
        response = app._database.read()
    except RuntimeError:
        msg = 'Database not updated. Please call update.'
        error = RuntimeError(msg)
        return error_to_response(error)

    response = response.replace({np.nan: None}).to_dict(orient='records')
    return Response(
        response=json.dumps(response),
        mimetype='application/json'
    )


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


@app.errorhandler(DataError)
def handle_data_error(error):
    '''
    Handles errors raise by config validation.

    Args:
        error (DataError): Config validation error.

    Returns:
        Response: DataError response.
    '''
    return error_to_response(error)  # pragma: no cover
# ------------------------------------------------------------------------------


app.register_error_handler(500, handle_data_error)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # pragma: no cover
