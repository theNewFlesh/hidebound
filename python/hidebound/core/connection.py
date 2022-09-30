from typing import Any

from lunchbox.enforce import Enforce
import dask.distributed as ddist
# ------------------------------------------------------------------------------


class DaskConnection:
    def __init__(self, cluster_type, num_workers):
        # type: (str, int) -> None
        '''
        Instantiates a DaskConnection.

        Args:
            cluster_type (str): Dask cluster type. Options include: local.
            num_workers (int): Number of Dask workers.

        Raises:
            EnforceError: If cluster_type is illegal.
            EnforceError: If num_workers is less than 1.
        '''
        msg = 'Illegal cluster type: {a}. Legal cluster types: {b}.'
        Enforce(cluster_type, 'in', ['local'], message=msg)

        msg = 'num_workers must be greater than 0. Given value: {a}.'
        Enforce(num_workers, '>=', 1, message=msg)
        # ----------------------------------------------------------------------

        self.cluster_type = cluster_type
        self.num_workers = num_workers
        self.cluster = None

    def __enter__(self):
        # type: () -> DaskConnection
        '''
        Creates Dask cluster and assigns it to self.cluster.

        Returns:
            DaskConnection: self.
        '''
        if self.cluster_type == 'local':
            self.cluster = ddist.LocalCluster(
                processes=True,
                n_workers=self.num_workers,
                dashboard_address='0.0.0.0:8087',
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # type: (Any, Any, Any, Any) -> None
        '''
        Closes Dask cluster.

        Args:
            exc_type (object): Required by python.
            exc_val (object): Required by python.
            exc_tb (object): Required by python.
        '''
        self.cluster.close()
