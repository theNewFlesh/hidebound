from copy import copy
import json

from flask import Flask, Response, request, redirect, url_for
from flasgger import Swagger, swag_from
from schematics.exceptions import DataError

from hidebound.database import Database
# ------------------------------------------------------------------------------


'''
Rolling-Pin Flask service.
'''


app = Flask(__name__)
swagger = Swagger(app)
__DATABASE = None
__CONFIG = None


@app.route('/api')
def index():
    return redirect(url_for('flasgger.apidocs'))


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
            description='Directory where hidebound directory will be created and hidebound data saved.',
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
    Initialize Database with given config.
    '''
    global __DATABASE
    global __CONFIG

    config = dict(
        specification_files=[],
        include_regex='',
        exclude_regex=r'\.DS_Store',
        write_mode='copy',
    )
    config.update(request.get_json())
    __DATABASE = Database.from_config(config)

    config = copy(config)
    config['specifications'] = [x.__name__.lower() for x in config['specifications']]
    __CONFIG = config
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
    Update Database with given config.
    '''
    global __DATABASE
    global __CONFIG

    __DATABASE.update()
    return Response(
        response=json.dumps(dict(
            message='Database updated.',
            config=__CONFIG,
        )),
        mimetype='application/json'
    )


def error_to_response(error):
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
    return error_to_response(error)


@app.errorhandler(AttributeError)
def handle_initialization_error(error):
    if "'NoneType' object has no attribute" in error.args[0]:
        if __DATABASE is None:
            error = RuntimeError('Database not initiliazed.')
            return error_to_response(error)
    raise error


app.register_error_handler(500, handle_data_error)
app.register_error_handler(500, handle_initialization_error)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
