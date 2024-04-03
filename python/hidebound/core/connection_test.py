from schematics.exceptions import DataError
import dask_gateway as dgw
import dask.distributed as ddist
import pytest

from hidebound.core.connection import DaskConnection, DaskConnectionConfig
# ------------------------------------------------------------------------------


# DASK-CONNECTION---------------------------------------------------------------
def test_dask_connection_init(dask_config):
    result = DaskConnection(dask_config)
    assert result.config == dask_config
    assert result.cluster is None


def test_dask_connection_enter(dask_config):
    with DaskConnection(dask_config) as result:
        assert isinstance(result, DaskConnection)
        assert isinstance(result.cluster, ddist.LocalCluster)
        assert len(result.cluster.workers) == 2
        assert result.cluster.status.name == 'running'


def test_dask_connection_exit(dask_config):
    with DaskConnection(dask_config) as result:
        pass
    assert result.cluster.status.name == 'closed'


def test_local_config(dask_config):
    result = DaskConnection(dask_config).local_config
    expected = dict(
        host='0.0.0.0',
        dashboard_address='0.0.0.0:8087',
        n_workers=dask_config['local_num_workers'],
        threads_per_worker=dask_config['local_threads_per_worker'],
        processes=dask_config['local_multiprocessing'],
    )
    assert result == expected


def test_gateway_config_basic(dask_config):
    dask_config['gateway_cluster_options'] = [
        dict(
            field='foobar', label='barfoo', default='a', option_type='select',
            options=['a', 'b']
        )
    ]
    result = DaskConnection(dask_config).gateway_config
    expected = dict(
        address=dask_config['gateway_address'],
        proxy_address=dask_config['gateway_proxy_address'],
        public_address=dask_config['gateway_public_address'],
        shutdown_on_close=dask_config['gateway_shutdown_on_close'],
    )
    assert isinstance(result['auth'], dgw.auth.BasicAuth)
    assert result['auth'].username == dask_config['gateway_api_user']
    assert result['auth'].password == dask_config['gateway_api_token']
    for key, val in expected.items():
        assert result[key] == val

    assert isinstance(result['cluster_options'], dgw.options.Options)
    assert result['cluster_options']['foobar'] == 'a'


def test_gateway_config_jupyterhub(dask_config):
    dask_config['gateway_cluster_options'] = [
        dict(
            field='foobar', label='barfoo', default='a', option_type='select',
            options=['a', 'b']
        )
    ]
    dask_config['gateway_auth_type'] = 'jupyterhub'
    result = DaskConnection(dask_config).gateway_config
    assert isinstance(result['auth'], dgw.JupyterHubAuth)
    assert result['auth'].api_token == dask_config['gateway_api_token']


def test_gateway_cluster_options(dask_config):
    dask_config['gateway_cluster_options'] = [dict(
        field='image',
        label='image',
        default='foobar:latest',
        option_type='string',
    )]
    result = DaskConnection(dask_config).gateway_config
    assert isinstance(result['cluster_options'], dgw.options.Options)
    assert result['cluster_options']['image'] == 'foobar:latest'


def test_cluster_type(dask_config):
    result = DaskConnection(dask_config).cluster_type
    assert result == dask_config['cluster_type']


def test_num_partitions(dask_config):
    result = DaskConnection(dask_config).num_partitions
    assert result == dask_config['num_partitions']


# DASK-CONNECTION-CONFIG--------------------------------------------------------
def test_dask_connection_config(dask_config):
    DaskConnectionConfig(dask_config).validate()


def test_config_cluster_type(dask_config):
    dask_config['cluster_type'] = 'local'
    DaskConnectionConfig(dask_config).validate()

    dask_config['cluster_type'] = 'gateway'
    DaskConnectionConfig(dask_config).validate()

    dask_config['cluster_type'] = 'foobar'
    with pytest.raises(DataError):
        DaskConnectionConfig(dask_config).validate()


def test_config_num_partitions(dask_config):
    dask_config['num_partitions'] = 0
    with pytest.raises(DataError):
        DaskConnectionConfig(dask_config).validate()


def test_config_local_num_workers(dask_config):
    dask_config['local_num_workers'] = 0
    with pytest.raises(DataError):
        DaskConnectionConfig(dask_config).validate()


def test_config_local_threads_per_worker(dask_config):
    dask_config['local_threads_per_worker'] = 0
    with pytest.raises(DataError):
        DaskConnectionConfig(dask_config).validate()


def test_config_gateway_address(dask_config):
    dask_config['gateway_address'] = 'http://proxy-public/services/dask-gateway'
    DaskConnectionConfig(dask_config).validate()


def test_config_gateway_proxy_address(dask_config):
    dask_config['gateway_proxy_address'] = 'gateway://traefik-daskhub-dask-gateway.core:80'
    DaskConnectionConfig(dask_config).validate()


def test_config_gateway_public_address(dask_config):
    dask_config['gateway_public_address'] = 'https://dask-gateway/services/dask-gateway/'
    DaskConnectionConfig(dask_config).validate()


def test_config_gateway_auth_type(dask_config):
    dask_config['gateway_auth_type'] = 'foobar'
    with pytest.raises(DataError):
        DaskConnectionConfig(dask_config).validate()


def test_config_gateway_cluster_options(dask_config):
    opts = [
        dict(field='bool', label='bool', default=True, option_type='bool'),
        dict(field='float', label='float', default=1.3, option_type='float'),
        dict(field='int', label='int', default=9, option_type='int'),
        dict(
            field='mapping', label='mapping', default={'a': 1},
            option_type='mapping'
        ),
        dict(
            field='select', label='select', default='a', option_type='select',
            options=['a', 'b']
        ),
        dict(field='string', label='string', default='a', option_type='string'),
    ]
    dask_config['gateway_cluster_options'] = opts
    DaskConnectionConfig(dask_config).validate()

    opts[0]['option_type'] = 'foobar'
    dask_config['gateway_cluster_options'] = opts
    with pytest.raises(DataError):
        DaskConnectionConfig(dask_config).validate()
