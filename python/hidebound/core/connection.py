from typing import Any

from schematics import Model
from schematics.types import (
    BaseType, BooleanType, IntType, ListType, ModelType, StringType, URLType
)
import dask_gateway as dgw
import dask.distributed as ddist

import hidebound.core.validators as vd
# ------------------------------------------------------------------------------


class DaskConnectionConfig(Model):
    r'''
    A class for validating DaskConnection configurations.

    Attributes:
        cluster_type (str, optional): Dask cluster type. Options include:
            local, gateway. Default: local.
        num_partitions (int, optional): Number of partions each DataFrame is to
            be split into. Default: 16.
        local_num_workers (int, optional): Number of workers to run on local
            cluster. Default: 16.
        local_threads_per_worker (int, optional): Number of threads to run per
            worker local cluster. Default: 1.
        local_multiprocessing (bool, optional): Whether to use multiprocessing
            for local cluster. Default: True.
        gateway_address (str, optional): Dask Gateway server address. Default:
            'http://proxy-public/services/dask-gateway'.
        gateway_proxy_address (str, optional): Dask Gateway scheduler proxy
            server address.
            Default: 'gateway://traefik-daskhub-dask-gateway.core:80'
        gateway_public_address (str, optional): The address to the gateway
            server, as accessible from a web browser.
            Default: 'https://dask-gateway/services/dask-gateway/'.
        gateway_auth_type (str, optional): Dask Gateway authentication type.
            Default: jupyterhub.
        gateway_api_token (str, optional): Authentication API token.
        gateway_cluster_options (list, optional): Dask Gateway cluster options.
            Default: [].
        gateway_shutdown_on_close (bool, optional): Whether to shudown cluster
            upon close. Default: True.
    '''
    cluster_type = StringType(
        required=True,
        default='local',
        validators=[lambda x: vd.is_in(x, ['local', 'gateway'])]
    )  # type: StringType
    num_partitions = IntType(
        required=True, default=16, validators=[lambda x: vd.is_gte(x, 1)]
    )  # type: IntType
    local_num_workers = IntType(
        required=True, default=16, validators=[lambda x: vd.is_gte(x, 1)]
    )  # type: IntType
    local_threads_per_worker = IntType(
        required=True, default=1, validators=[lambda x: vd.is_gte(x, 1)]
    )  # type: IntType
    local_multiprocessing = BooleanType(
        required=True, default=True
    )  # type: BooleanType
    gateway_address = URLType(
        required=True,
        fqdn=False,
        default='http://proxy-public/services/dask-gateway',
    )  # type: URLType
    gateway_proxy_address = StringType(
        required=True,
        default='gateway://traefik-daskhub-dask-gateway.core:80',
    )  # type: StringType
    gateway_public_address = URLType(
        required=True,
        fqdn=False,
        default='https://dask-gateway/services/dask-gateway/',
    )  # type: URLType
    gateway_auth_type = StringType(
        required=True,
        default='jupyterhub',
        validators=[lambda x: vd.is_eq(x, 'jupyterhub')]
    )  # StringType
    gateway_api_token = StringType()  # StringType
    gateway_shutdown_on_close = BooleanType(
        required=True, default=True
    )  # type: BooleanType

    class ClusterOption(Model):
        field = StringType(required=True)  # type: StringType
        label = StringType(required=True)  # type: StringType
        default = BaseType(required=True)  # type: BaseType
        options = ListType(BaseType, required=True, default=[])
        option_type = StringType(
            required=True, validators=[vd.is_cluster_option_type]
        )
    gateway_cluster_options = ListType(
        ModelType(ClusterOption), required=False, default=[]
    )  # type: ListType
# ------------------------------------------------------------------------------


class DaskConnection:
    def __init__(self, config):
        # type: (dict) -> None
        '''
        Instantiates a DaskConnection.

        Args:
            config (dict): DaskConnection config.

        Raises:
            DataError: If config is invalid.
        '''
        config = DaskConnectionConfig(config)
        config.validate()
        self.config = config.to_native()
        self.cluster = None

    @property
    def local_config(self):
        # type: () -> dict
        '''
        Returns:
            dict: Local cluster config.
        '''
        return dict(
            host='0.0.0.0',
            dashboard_address='0.0.0.0:8087',
            n_workers=self.config['local_num_workers'],
            threads_per_worker=self.config['local_threads_per_worker'],
            processes=self.config['local_multiprocessing'],
        )

    @property
    def gateway_config(self):
        # type: () -> dict
        '''
        Returns:
            dict: gateway cluster config.
        '''
        # create gateway config
        output = dict(
            address=self.config['gateway_address'],
            proxy_address=self.config['gateway_proxy_address'],
            public_address=self.config['gateway_public_address'],
            shutdown_on_close=self.config['gateway_shutdown_on_close'],
        )

        # set jupyterhub authentication
        if self.config['gateway_auth_type'] == 'jupyterhub':
            output['auth'] = dgw.JupyterHubAuth(
                api_token=self.config['gateway_api_token']
            )

        # set cluster options
        opts = self.config['gateway_cluster_options']
        if len(opts) > 0:
            specs = []
            for opt in opts:
                spec = dict(
                    field=opt['field'],
                    label=opt['label'],
                    default=opt['default'],
                    spec={'type': opt['option_type']},
                )
                if opt['option_type'] == 'select':
                    spec['spec']['options'] = opt['options']
                specs.append(spec)
            options = dgw.options.Options._from_spec(specs)
            output['cluster_options'] = options

        return output

    @property
    def cluster_type(self):
        # type: () -> str
        '''
        Returns:
            str: Cluster type.
        '''
        return self.config['cluster_type']

    @property
    def num_partitions(self):
        # type: () -> int
        '''
        Returns:
            int: Number of partitions.
        '''
        return self.config['num_partitions']

    def __enter__(self):
        # type: () -> DaskConnection
        '''
        Creates Dask cluster and assigns it to self.cluster.

        Returns:
            DaskConnection: self.
        '''
        if self.cluster_type == 'local':
            self.cluster = ddist.LocalCluster(**self.local_config)
        elif self.cluster_type == 'gateway':  # pragma: no cover
            self.cluster = dgw.GatewayCluster(**self.gateway_config)  # pragma: no cover
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
