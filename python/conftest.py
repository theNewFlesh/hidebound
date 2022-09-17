from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os

import flask
import lunchbox.tools as lbt
import pytest
import yaml

from hidebound.core.database_test_base import *  # noqa: F403 F401
import hidebound.server.extensions as ext
# ------------------------------------------------------------------------------


@pytest.fixture()
def env(config):
    yaml_keys = [
        'specification_files',
        'exporters',
        'webhooks',
    ]
    for key, val in config.items():
        if key in yaml_keys:
            os.environ[f'HIDEBOUND_{key.upper()}'] = yaml.safe_dump(val)
        else:
            os.environ[f'HIDEBOUND_{key.upper()}'] = str(val)

    keys = filter(lambda x: x.startswith('HIDEBOUND_'), os.environ.keys())
    env = {k: os.environ[k] for k in keys}
    yield env

    keys = filter(lambda x: x.startswith('HIDEBOUND_'), os.environ.keys())
    for key in keys:
        os.environ.pop(key)


@pytest.fixture()
def app():
    context = flask.Flask(__name__).app_context()
    context.push()
    app = context.app
    app.config['TESTING'] = True

    yield app

    context.pop()


@pytest.fixture()
def client(app):
    # set instance members
    client = app.test_client()
    yield client


@pytest.fixture()
def extension(app, make_dirs):
    app.config['TESTING'] = False
    ext.swagger.init_app(app)
    ext.hidebound.init_app(app)
    yield ext.hidebound
    ext.hidebound.database._stop_cluster()


@pytest.fixture()
def temp_dir():
    temp = TemporaryDirectory()
    yield temp.name
    temp.cleanup()


@pytest.fixture()
def make_dirs(temp_dir):
    ingress = Path(temp_dir, 'ingress').as_posix()
    staging = Path(temp_dir, 'hidebound').as_posix()
    archive = Path(temp_dir, 'archive').as_posix()

    # creates dirs
    os.makedirs(ingress)
    os.makedirs(staging)
    os.makedirs(archive)

    yield ingress, staging, archive


@pytest.fixture()
def config(temp_dir):
    spec = '../hidebound/hidebound/core/test_specifications.py'
    if 'REPO_ENV' in os.environ:
        spec = '../python/hidebound/core/test_specifications.py'
    spec = lbt.relative_path(__file__, spec).absolute().as_posix()

    config = dict(
        ingress_directory=Path(temp_dir, 'ingress').as_posix(),
        staging_directory=Path(temp_dir, 'hidebound').as_posix(),
        include_regex='',
        exclude_regex=r'\.DS_Store',
        write_mode='copy',
        dask_workers=2,
        dask_cluster_type='local',
        redact_regex='(_key|_id|url)$',
        redact_hash=True,
        workflow=['update', 'create', 'export', 'delete'],
        specification_files=[spec],
        exporters=[
            dict(
                name='disk',
                target_directory=Path(temp_dir, 'archive').as_posix(),
                metadata_types=['asset', 'file', 'asset-chunk', 'file-chunk']
            )
        ],
        webhooks=[
            dict(
                url='http://foobar.com/api/user?',
                method='get',
                params={'id': 123},
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                }
            )
        ]
    )
    return config


@pytest.fixture()
def config_yaml_file(temp_dir, config):
    filepath = Path(temp_dir, 'hidebound_config.yaml').as_posix()
    with open(filepath, 'w') as f:
        yaml.safe_dump(config, f)

    os.environ['HIDEBOUND_CONFIG_FILEPATH'] = filepath
    return filepath


@pytest.fixture()
def config_json_file(temp_dir, config):
    filepath = Path(temp_dir, 'hidebound_config.json').as_posix()
    with open(filepath, 'w') as f:
        json.dump(config, f)

    os.environ['HIDEBOUND_CONFIG_FILEPATH'] = filepath
    return filepath
