import re

from lunchbox.enforce import EnforceError
import dask.distributed as ddist
import pytest

from hidebound.core.connection import DaskConnection
# ------------------------------------------------------------------------------


DASK_WORKERS = 2
RERUNS = 3
DELAY = 1


# DASK-CONNECTION---------------------------------------------------------------
def test_dask_connection_init():
    result = DaskConnection('local', 9)
    assert result.cluster_type == 'local'
    assert result.num_workers == 9


def test_dask_connection_init_errors():
    with pytest.raises(EnforceError) as e:
        DaskConnection('foobar', 9)
    expected = 'Illegal cluster type: foobar. Legal cluster types:.*local'
    assert re.search(expected, str(e.value))

    with pytest.raises(EnforceError) as e:
        DaskConnection('local', 0)
    expected = 'num_workers must be greater than 0. Given value: 0.'
    assert re.search(expected, str(e.value))


def test_dask_connection_enter():
    with DaskConnection('local', 9) as result:
        assert isinstance(result, DaskConnection)
        assert isinstance(result.cluster, ddist.LocalCluster)
        assert len(result.cluster.workers) == 9
        assert result.cluster.status.name == 'running'


def test_dask_connection_exit():
    with DaskConnection('local', 9) as result:
        pass
    assert result.cluster.status.name == 'closed'
