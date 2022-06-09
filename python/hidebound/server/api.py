from typing import Any, Optional, Union

from json import JSONDecodeError
from pathlib import Path
import json
import os

from schematics.exceptions import DataError
from werkzeug.exceptions import BadRequest
import flasgger as swg
import flask
import jsoncomment as jsonc
import numpy as np
import yaml

from hidebound.core.database import Database
import hidebound.server.server_tools as server_tools
# ------------------------------------------------------------------------------


class ApiExtension:
    def __init__(self, app=None):
        # type: (Optional[flask.Flask]) -> None
        '''
        Initialize flask extension.

        Args:
            app (flask.Flask, optional): Flask app.
        '''
        self.config = None  # type: Optional[dict]
        self.database = None  # type: Optional[Database]
        self.app = None  # type: Optional[flask.Flask]
        self.disconnect()
        if app is not None:
            self.init_app(app)

    def _get_config(self, app):
        # type: (flask.Flask) -> dict
        '''
        Get config from envirnment variables or config file.

        Args:
            app (flask.Flask): Flask app.

        Returns:
            dict: Database config.
        '''
        config_path = os.environ.get('HIDEBOUND_CONFIG_FILEPATH', None)
        if config_path is not None:
            return self._get_config_from_file(config_path)

        app.config.from_prefixed_env('HIDEBOUND')
        return self._get_config_from_env(app)

    def _get_config_from_file(self, filepath):
        # type: (Union[str, Path]) -> dict
        '''
        Get config from envirnment variables or config file.

        Args:
            filepath (str or Path): Filepath of hidebound config.

        Raises:
            FileNotFoundError: If HIDEBOUND_CONFIG_FILEPATH is set to a file
                that does not end in json, yml or yaml.

        Returns:
            dict: Database config.
        '''
        fp = Path(filepath).as_posix()
        ext = os.path.splitext(fp)[-1].lower().lstrip('.')
        exts = ['json', 'yml', 'yaml']
        if ext not in exts:
            msg = f'Hidebound config file {fp} must have one of these '
            msg += f'extensions: {exts}.'
            raise FileNotFoundError(msg)

        with open(filepath) as f:
            if ext in ['yml', 'yaml']:
                return yaml.safe_load(f)
            return jsonc.JsonComment().load(f)

    def _get_config_from_env(self, app):
        # type: (flask.Flask) -> dict
        '''
        Get config from environment variables.

        Args:
            app (flask.Flask): Flask app.

        Returns:
            dict: Database config.
        '''
        dask_enabled = str(app.config.get('DASK_ENABLED', False))  # type: Any
        if dask_enabled.lower() == 'true':
            dask_enabled = True
        elif dask_enabled.lower() == 'false':
            dask_enabled = False

        return dict(
            root_directory=app.config.get('ROOT_DIRECTORY'),
            hidebound_directory=app.config.get('HIDEBOUND_DIRECTORY'),
            include_regex=app.config.get('INCLUDE_REGEX', ''),
            exclude_regex=app.config.get('EXCLUDE_REGEX', r'\.DS_Store'),
            write_mode=app.config.get('WRITE_MODE', 'copy'),
            dask_enabled=dask_enabled,
            dask_workers=int(app.config.get('DASK_WORKERS', 8)),
            specification_files=yaml.safe_load(
                app.config.get('SPECIFICATION_FILES', '[]')
            ),
            exporters=yaml.safe_load(app.config.get('EXPORTERS', '{}')),
            webhooks=yaml.safe_load(app.config.get('WEBHOOKS', '[]')),
        )

    def init_app(self, app):
        # type: (flask.Flask) -> None
        '''
        Add endpoints and error handlers to given app.
        Assigns given app to self.app.

        Args:
            app (Flask): Flask app.
        '''
        # register routes
        app.add_url_rule('/api', methods=['GET'], view_func=self.api)
        app.add_url_rule('/api/initialize', methods=['POST'], view_func=self.initialize)
        app.add_url_rule('/api/create', methods=['POST'], view_func=self.create)
        app.add_url_rule('/api/read', methods=['GET', 'POST'], view_func=self.read)
        app.add_url_rule('/api/update', methods=['POST'], view_func=self.update)
        app.add_url_rule('/api/delete', methods=['POST'], view_func=self.delete)
        app.add_url_rule('/api/export', methods=['POST'], view_func=self.export)
        app.add_url_rule('/api/search', methods=['POST'], view_func=self.search)
        app.add_url_rule('/api/workflow', methods=['POST'], view_func=self.workflow)

        # register error handlers
        app.register_error_handler(DataError, self.handle_data_error)
        app.register_error_handler(KeyError, self.handle_key_error)
        app.register_error_handler(TypeError, self.handle_type_error)
        app.register_error_handler(JSONDecodeError, self.handle_json_decode_error)

        self.app = app
        setattr(self.app, 'api', self)

    def connect(self):
        # type: () -> None
        '''
        Create hidebound database and config.
        Gets config from environment variables and assigns it to self.config.
        Create a Database instance from config and assign it to self.database.
        '''
        self.config = self._get_config(self.app)
        self.database = Database.from_config(self.config)  # type: ignore

    def disconnect(self):
        # type: () -> None
        '''
        Sets self.config and self.database to None.
        '''
        self.config = None
        self.database = None

    def api(self):
        # type: () -> Any
        '''
        Route to Hidebound API documentation.

        Returns:
            html: Flassger generated API page.
        '''
        # TODO: Test this with selenium.
        return flask.redirect(flask.url_for('flasgger.apidocs'))

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
    def initialize(self):
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
            return server_tools.get_config_error()
        if not isinstance(config, dict):
            return server_tools.get_config_error()

        self.database = Database.from_config(config)

        return flask.Response(
            response=json.dumps(dict(message='Database initialized.')),
            mimetype='application/json'
        )

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
    def create(self):
        # type: () -> flask.Response
        '''
        Create hidebound data.

        Returns:
            Response: Flask Response instance.
        '''
        if self.database is None:
            return server_tools.get_initialization_error()

        try:
            self.database.create()
        except RuntimeError:
            return server_tools.get_update_error()

        return flask.Response(
            response=json.dumps(dict(message='Hidebound data created.')),
            mimetype='application/json'
        )

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
    def read(self):
        # type: () -> flask.Response
        '''
        Read database.

        Returns:
            Response: Flask Response instance.
        '''
        if self.database is None:
            return server_tools.get_initialization_error()

        params = flask.request.get_json()  # type: Any
        grp = False
        if params not in [None, {}]:
            try:
                params = json.loads(params)
                grp = params['group_by_asset']
                assert(isinstance(grp, bool))
            except (JSONDecodeError, TypeError, KeyError, AssertionError):
                return server_tools.get_read_error()

        response = {}  # type: Any
        try:
            response = self.database.read(group_by_asset=grp)
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
    def update(self):
        # type: () -> flask.Response
        '''
        Update database.

        Returns:
            Response: Flask Response instance.
        '''
        if self.database is None:
            return server_tools.get_initialization_error()

        self.database.update()
        return flask.Response(
            response=json.dumps(dict(message='Database updated.')),
            mimetype='application/json'
        )

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
    def delete(self):
        # type: () -> flask.Response
        '''
        Delete hidebound data.

        Returns:
            Response: Flask Response instance.
        '''
        if self.database is None:
            return server_tools.get_initialization_error()

        self.database.delete()
        return flask.Response(
            response=json.dumps(dict(message='Hidebound data deleted.')),
            mimetype='application/json'
        )

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
    def export(self):
        # type: () -> flask.Response
        '''
        Export hidebound data.

        Returns:
            Response: Flask Response instance.
        '''
        if self.database is None:
            return server_tools.get_initialization_error()

        try:
            self.database.export()
        except Exception as error:
            return server_tools.error_to_response(error)

        return flask.Response(
            response=json.dumps(dict(message='Hidebound data exported.')),
            mimetype='application/json'
        )

    @swg.swag_from(dict(
        parameters=[
            dict(
                name='query',
                type='string',
                description='SQL query for searching database. Make sure to use "FROM data" in query.',  # noqa: E501
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
    def search(self):
        # type: () -> flask.Response
        '''
        Search database with a given SQL query.

        Returns:
            Response: Flask Response instance.
        '''
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

        if self.database is None:
            return server_tools.get_initialization_error()

        if self.database.data is None:
            return server_tools.get_update_error()

        response = None
        try:
            response = self.database.search(query, group_by_asset=grp)
        except Exception as e:
            return server_tools.error_to_response(e)

        response.asset_valid = response.asset_valid.astype(bool)
        response = response.replace({np.nan: None}).to_dict(orient='records')
        response = {'response': response}
        return flask.Response(
            response=json.dumps(response),
            mimetype='application/json'
        )

    @swg.swag_from(dict(
        parameters=[
            dict(
                name='workflow',
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
    def workflow(self):
        # type: () -> flask.Response
        '''
        Run given hidebound workflow.

        Returns:
            Response: Flask Response instance.
        '''
        params = flask.request.get_json()  # type: Any
        params = json.loads(params)
        workflow = params['workflow']

        # get and validate workflow steps
        legal = ['update', 'create', 'export', 'delete']
        diff = sorted(list(set(workflow).difference(legal)))
        if len(diff) > 0:
            msg = f'Found illegal workflow steps: {diff}. Legal steps: {legal}.'
            return server_tools.error_to_response(ValueError(msg))

        # run through workflow
        for step in workflow:
            try:
                getattr(self.database, step)()
            except Exception as error:  # pragma: no cover
                return server_tools.error_to_response(error)  # pragma: no cover

        return flask.Response(
            response=json.dumps(dict(
                message='Workflow completed.', workflow=workflow)),
            mimetype='application/json'
        )

    def handle_data_error(self, error):
        # type: (DataError) -> flask.Response
        '''
        Handles errors raise by config validation.

        Args:
            error (DataError): Config validation error.

        Returns:
            Response: DataError response.
        '''
        return server_tools.error_to_response(error)

    def handle_key_error(self, error):
        # type: (KeyError) -> flask.Response
        '''
        Handles key errors.

        Args:
            error (KeyError): Key error.

        Returns:
            Response: KeyError response.
        '''
        return server_tools.error_to_response(error)

    def handle_type_error(self, error):
        # type: (TypeError) -> flask.Response
        '''
        Handles key errors.

        Args:
            error (TypeError): Key error.

        Returns:
            Response: TypeError response.
        '''
        return server_tools.error_to_response(error)

    def handle_json_decode_error(self, error):
        # type: (JSONDecodeError) -> flask.Response
        '''
        Handles key errors.

        Args:
            error (JSONDecodeError): Key error.

        Returns:
            Response: JSONDecodeError response.
        '''
        return server_tools.error_to_response(error)
