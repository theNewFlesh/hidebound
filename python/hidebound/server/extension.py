from typing import Optional, Union

from pathlib import Path
import os

import flask
import pyjson5 as jsonc
import yaml

from hidebound.core.database import Database
from hidebound.server.api import API
import hidebound.core.config as hbc
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
            config = self._get_config_from_file(config_path)

        else:
            app.config.from_prefixed_env('HIDEBOUND')
            config = self._get_config_from_env(app)

        config = hbc.Config(config).to_native()
        return config

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
            return jsonc.load(f)

    def _get_config_from_env(self, app):
        # type: (flask.Flask) -> dict
        '''
        Get config from environment variables.

        Args:
            app (flask.Flask): Flask app.

        Returns:
            dict: Database config.
        '''
        dask = dict(
            cluster_type=app.config.get('DASK_CLUSTER_TYPE'),
            num_partitions=app.config.get('DASK_NUM_PARTITIONS'),
            local_num_workers=app.config.get('DASK_LOCAL_NUM_WORKERS'),
            local_threads_per_worker=app.config.get('DASK_LOCAL_THREADS_PER_WORKER'),
            local_multiprocessing=hbt.str_to_bool(
                app.config.get('DASK_LOCAL_MULTIPROCESSING', 'True')
            ),
            gateway_address=app.config.get('DASK_GATEWAY_ADDRESS'),
            gateway_proxy_address=app.config.get('DASK_GATEWAY_PROXY_ADDRESS'),
            gateway_public_address=app.config.get('DASK_GATEWAY_PUBLIC_ADDRESS'),
            gateway_auth_type=app.config.get('DASK_GATEWAY_AUTH_TYPE'),
            gateway_api_token=app.config.get('DASK_GATEWAY_API_TOKEN'),
            gateway_cluster_options=yaml.safe_load(
                str(app.config.get('DASK_GATEWAY_CLUSTER_OPTIONS', '[]'))
            ),
            gateway_shutdown_on_close=hbt.str_to_bool(
                app.config.get('DASK_GATEWAY_SHUTDOWN_ON_CLOSE', 'True')
            ),
        )
        return dict(
            ingress_directory=app.config.get('INGRESS_DIRECTORY'),
            staging_directory=app.config.get('STAGING_DIRECTORY'),
            include_regex=app.config.get('INCLUDE_REGEX', ''),
            exclude_regex=app.config.get('EXCLUDE_REGEX', r'\.DS_Store'),
            write_mode=app.config.get('WRITE_MODE', 'copy'),
            redact_regex=app.config.get('REDACT_REGEX', '(_key|_id|_token|url)$'),
            redact_hash=hbt.str_to_bool(app.config.get('REDACT_HASH', 'False')),
            specification_files=yaml.safe_load(
                str(app.config.get('SPECIFICATION_FILES', '[]'))
            ),
            workflow=yaml.safe_load(str(app.config.get(
                'WORKFLOW',
                '["delete", "update", "create", "export"]',
            ))),
            dask=dask,
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
