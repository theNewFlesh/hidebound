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
        assert len(result.cluster.workers) == 4
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


def test_gateway_config(dask_config):
    result = DaskConnection(dask_config).gateway_config
    expected = dict(
        address=dask_config['gateway_address'],
        proxy_address=dask_config['gateway_proxy_address'],
        public_address=dask_config['gateway_public_address'],
        shutdown_on_close=dask_config['gateway_shutdown_on_close'],
    )
    assert isinstance(result['auth'], dgw.JupyterHubAuth)
    assert result['auth'].api_token == dask_config['gateway_api_token']
    for key, val in expected.items():
        assert result[key] == val


def test_cluster_type(dask_config):
    result = DaskConnection(dask_config).cluster_type
    assert result == dask_config['cluster_type']


def test_num_partitions(dask_config):
    result = DaskConnection(dask_config).num_partitions
    assert result == dask_config['num_partitions']


# DASK-CONNECTION-CONFIG--------------------------------------------------------
def test_dask_connection_config(dask_config):
    DaskConnectionConfig(dask_config).validate()

    # cluster type
    config = dask_config.copy()
    config['cluster_type'] = 'local'
    DaskConnectionConfig(config).validate()

    config['cluster_type'] = 'gateway'
    DaskConnectionConfig(config).validate()

    config['cluster_type'] = 'foobar'
    with pytest.raises(DataError):
        DaskConnectionConfig(config).validate()

    # num_partitions
    config = dask_config.copy()
    config['num_partitions'] = 0
    with pytest.raises(DataError):
        DaskConnectionConfig(config).validate()

    # local_num_workers
    config = dask_config.copy()
    config['local_num_workers'] = 0
    with pytest.raises(DataError):
        DaskConnectionConfig(config).validate()

    # local_threads_per_worker
    config = dask_config.copy()
    config['local_threads_per_worker'] = 0
    with pytest.raises(DataError):
        DaskConnectionConfig(config).validate()

    # gateway_address
    config = dask_config.copy()
    config['gateway_address'] = 'http://proxy-public/services/dask-gateway'
    DaskConnectionConfig(config).validate()

    # gateway_proxy_address
    config = dask_config.copy()
    config['gateway_proxy_address'] = 'gateway://traefik-daskhub-dask-gateway.core:80'
    DaskConnectionConfig(config).validate()

    # gateway_public_address
    config = dask_config.copy()
    config['gateway_public_address'] = 'https://dask-gateway/services/dask-gateway/'
    DaskConnectionConfig(config).validate()

    # gateway_auth_type
    config = dask_config.copy()
    config['gateway_auth_type'] = 'foobar'
    with pytest.raises(DataError):
        DaskConnectionConfig(config).validate()
