import os

import pytest

from hidebound.core.database import Database
from hidebound.server.api import API
from hidebound.server.extension import HideboundExtension
# ------------------------------------------------------------------------------


def test_init(env, app, config, make_dirs):
    result = HideboundExtension(app=None)
    assert hasattr(result, 'config') is False
    assert hasattr(result, 'database') is False

    app.config['TESTING'] = False
    result = HideboundExtension(app=app)
    assert hasattr(result, 'config')
    assert hasattr(result, 'database')
    assert result.config == config
    assert isinstance(result.database, Database)


def test_get_config_from_env(env, app, config):
    app.config.from_prefixed_env('HIDEBOUND')
    result = HideboundExtension()._get_config_from_env(app)
    for key, val in config.items():
        assert result[key] == val


def test_get_config_from_env_bool(env, app, config):
    config['dask_enabled'] = True
    os.environ['HIDEBOUND_DASK_ENABLED'] = 'True'
    app.config.from_prefixed_env('HIDEBOUND')
    result = HideboundExtension()._get_config_from_env(app)
    for key, val in config.items():
        assert result[key] == val


def test_get_config_from_yaml_file(env, app, config, config_yaml_file):
    result = HideboundExtension()._get_config_from_file(config_yaml_file)
    for key, val in config.items():
        assert result[key] == val


def test_get_config_from_json_file(env, app, config, config_json_file):
    result = HideboundExtension()._get_config_from_file(config_json_file)
    for key, val in config.items():
        assert result[key] == val


def test_get_config_from_file_error(env, app, config):
    expected = 'Hidebound config files must end in one of these extensions:'
    expected += r" \['json', 'yml', 'yaml'\]\. Given file: "
    expected += r'/foo/bar/config\.pizza\.'
    with pytest.raises(FileNotFoundError, match=expected):
        HideboundExtension()._get_config_from_file('/foo/bar/config.pizza')


def test_get_config_env_vars(env, app, config):
    app.config.from_prefixed_env('HIDEBOUND')
    result = HideboundExtension()._get_config(app)
    for key, val in config.items():
        assert result[key] == val


def test_get_config_env_vars_empty_lists(env, app, config):
    os.environ['HIDEBOUND_SPECIFICATION_FILES'] = '[]'
    os.environ['HIDEBOUND_WEBHOOKS'] = '[]'
    app.config.from_prefixed_env('HIDEBOUND')

    result = HideboundExtension()._get_config(app)['specification_files']
    assert result == []

    result = HideboundExtension()._get_config(app)['webhooks']
    assert result == []


def test_get_config_filepath(env, app, config, config_yaml_file):
    os.environ['HIDEBOUND_ROOT_DIRECTORY'] = 'foobar'
    app.config.from_prefixed_env('HIDEBOUND')
    result = HideboundExtension()._get_config(app)

    assert result['root_directory'] != 'foobar'

    for key, val in config.items():
        assert result[key] == val


def test_init_app(env, app, config, make_dirs):
    app.config['TESTING'] = False
    hb = HideboundExtension()
    hb.init_app(app)

    assert app.extensions['hidebound'] is hb
    assert app.blueprints['hidebound_api'] is API
    assert hasattr(hb, 'config')
    assert hasattr(hb, 'database')
    assert hb.config == config
    assert isinstance(hb.database, Database)


def test_init_app_testing(env, app, config):
    app.config['TESTING'] = True
    hb = HideboundExtension()
    hb.init_app(app)

    assert app.extensions['hidebound'] is hb
    assert app.blueprints['hidebound_api'] is API
    assert hasattr(hb, 'config') is False
    assert hasattr(hb, 'database') is False
