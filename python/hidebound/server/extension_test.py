import os

import pytest

from hidebound.core.database import Database
from hidebound.server.api import API
from hidebound.server.extension import HideboundExtension
# ------------------------------------------------------------------------------


def test_init(env, flask_app, config, make_dirs):
    result = HideboundExtension(app=None)
    assert hasattr(result, 'config') is False
    assert hasattr(result, 'database') is False

    flask_app.config['TESTING'] = False
    result = HideboundExtension(app=flask_app)
    assert hasattr(result, 'config')
    assert hasattr(result, 'database')
    assert result.config == config
    assert isinstance(result.database, Database)


def test_get_config_from_env(env, flask_app, config):
    flask_app.config.from_prefixed_env('HIDEBOUND')
    result = HideboundExtension()._get_config_from_env(flask_app)
    for key, val in config.items():
        assert result[key] == val


def test_get_config_from_env_bool(env, flask_app, config):
    config['dask_enabled'] = True
    os.environ['HIDEBOUND_DASK_ENABLED'] = 'True'
    flask_app.config.from_prefixed_env('HIDEBOUND')
    result = HideboundExtension()._get_config_from_env(flask_app)
    for key, val in config.items():
        assert result[key] == val


def test_get_config_from_yaml_file(env, flask_app, config, config_yaml_file):
    result = HideboundExtension()._get_config_from_file(config_yaml_file)
    for key, val in config.items():
        assert result[key] == val


def test_get_config_from_json_file(env, flask_app, config, config_json_file):
    result = HideboundExtension()._get_config_from_file(config_json_file)
    for key, val in config.items():
        assert result[key] == val


def test_get_config_from_file_error(env, flask_app, config):
    expected = 'Hidebound config files must end in one of these extensions:'
    expected += r" \['json', 'yml', 'yaml'\]\. Given file: "
    expected += r'/foo/bar/config\.pizza\.'
    with pytest.raises(FileNotFoundError, match=expected):
        HideboundExtension()._get_config_from_file('/foo/bar/config.pizza')


def test_get_config_env_vars(env, flask_app, config):
    flask_app.config.from_prefixed_env('HIDEBOUND')
    result = HideboundExtension()._get_config(flask_app)
    for key, val in config.items():
        assert result[key] == val


def test_get_config_mising_env_var(env, flask_app, config):
    os.environ.pop('HIDEBOUND_WORKFLOW')
    flask_app.config.from_prefixed_env('HIDEBOUND')
    result = HideboundExtension()._get_config(flask_app)['workflow']
    expected = ['delete', 'update', 'create', 'export']
    assert result == expected


def test_get_config_env_vars_empty_lists(env, flask_app, config):
    os.environ['HIDEBOUND_WORKFLOW'] = '[]'
    os.environ['HIDEBOUND_SPECIFICATION_FILES'] = '[]'
    os.environ['HIDEBOUND_WEBHOOKS'] = '[]'
    flask_app.config.from_prefixed_env('HIDEBOUND')

    keys = ['workflow', 'specification_files', 'webhooks']
    for key in keys:
        result = HideboundExtension()._get_config(flask_app)[key]
        assert result == []


def test_get_config_filepath(env, flask_app, config, config_yaml_file):
    os.environ['HIDEBOUND_INGRESS_DIRECTORY'] = 'foobar'
    flask_app.config.from_prefixed_env('HIDEBOUND')
    result = HideboundExtension()._get_config(flask_app)

    assert result['ingress_directory'] != 'foobar'

    for key, val in config.items():
        assert result[key] == val


def test_init_app(env, flask_app, config, make_dirs):
    flask_app.config['TESTING'] = False
    hb = HideboundExtension()
    hb.init_app(flask_app)

    assert flask_app.extensions['hidebound'] is hb
    assert flask_app.blueprints['hidebound_api'] is API
    assert hasattr(hb, 'config')
    assert hasattr(hb, 'database')
    assert hb.config == config
    assert isinstance(hb.database, Database)


def test_init_app_testing(env, flask_app, config):
    flask_app.config['TESTING'] = True
    hb = HideboundExtension()
    hb.init_app(flask_app)

    assert flask_app.extensions['hidebound'] is hb
    assert flask_app.blueprints['hidebound_api'] is API
    assert hasattr(hb, 'config') is False
    assert hasattr(hb, 'database') is False
