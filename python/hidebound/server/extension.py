from typing import Optional, Union

from pathlib import Path
import os

import flask
import jsoncomment as jsonc
import yaml

from hidebound.core.database import Database
from hidebound.server.api import API
import hidebound.core.tools as hbt
# ------------------------------------------------------------------------------


# inheriting from Singleton breaks init and init_app tests
class HideboundExtension:
    def __init__(self, app=None):
        # type: (Optional[flask.Flask]) -> None
        '''
        Initialize flask extension.

        Args:
            app (flask.Flask, optional): Flask app.
        '''
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
        fp = Path(filepath)
        ext = fp.suffix.lower().lstrip('.')
        exts = ['json', 'yml', 'yaml']
        if ext not in exts:
            msg = 'Hidebound config files must end in one of these extensions: '
            msg += f'{exts}. Given file: {fp.as_posix()}.'
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
        return dict(
            root_directory=app.config.get('ROOT_DIRECTORY'),
            hidebound_directory=app.config.get('HIDEBOUND_DIRECTORY'),
            include_regex=app.config.get('INCLUDE_REGEX', ''),
            exclude_regex=app.config.get('EXCLUDE_REGEX', r'\.DS_Store'),
            write_mode=app.config.get('WRITE_MODE', 'copy'),
            dask_enabled=hbt.str_to_bool(app.config.get('DASK_ENABLED', 'False')),
            dask_workers=int(app.config.get('DASK_WORKERS', 8)),
            specification_files=yaml.safe_load(
                str(app.config.get('SPECIFICATION_FILES', '[]'))
            ),
            exporters=yaml.safe_load(str(app.config.get('EXPORTERS', '{}'))),
            webhooks=yaml.safe_load(str(app.config.get('WEBHOOKS', '[]'))),
        )

    def init_app(self, app):
        # type: (flask.Flask) -> None
        '''
        Add endpoints and error handlers to given app.

        Args:
            app (Flask): Flask app.
        '''
        app.extensions['hidebound'] = self
        app.register_blueprint(API)
        if not app.config['TESTING']:
            self.config = self._get_config(app)
            self.database = Database.from_config(self.config)
