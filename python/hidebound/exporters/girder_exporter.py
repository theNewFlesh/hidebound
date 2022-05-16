from typing import Any, Dict, List, Union

from pathlib import Path

from schematics import Model
from schematics.types import IntType, ListType, StringType, URLType
import girder_client

from hidebound.exporters.exporter_base import ExporterBase
import hidebound.core.validators as vd
# ------------------------------------------------------------------------------


class GirderConfig(Model):
    '''
    A class for validating configurations supplied to GirderExporter.

    Attributes:
        api_key (str): Girder API key.
        root_id (str): ID of folder or collection under which all data will
            be exported.
        root_type (str, optional): Root entity type. Default: collection.
            Options: folder, collection
        host (str, optional): Docker host URL address. Default: http://0.0.0.0
        port (int, optional): Docker host port. Default: 8180.
        metadata_types (list, optional): List of metadata types for export.
            Default: [asset, file].
    '''
    api_key = StringType(required=True)  # type: StringType
    root_id = StringType(required=True)  # type: StringType
    root_type = StringType(
        required=True,
        default='collection',
        validators=[lambda x: vd.is_in([x], ['collection', 'folder'])]
    )  # type: StringType
    host = URLType(required=True, default='http://0.0.0.0')  # type: URLType
    port = IntType(
        required=True,
        default=8180,
        validators=[
            lambda x: vd.is_lt(x, 65536),
            lambda x: vd.is_gt(x, 1023),
        ]
    )  # type: IntType
    metadata_types = ListType(
        StringType(validators=[vd.is_metadata_type]),
        required=True,
        default=['asset', 'file']
    )


class GirderExporter(ExporterBase):
    '''
    Export for Girder asset framework.
    '''
    @staticmethod
    def from_config(config, client=None):
        # type: (Dict, Any) -> GirderExporter
        '''
        Construct a GirderExporter from a given config.

        Args:
            config (dict): Config dictionary.
            client (object, optional): Client instance, for testing.
                Default: None.

        Raises:
            DataError: If config is invalid.

        Returns:
            GirderExporter: GirderExporter instance.
        '''
        return GirderExporter(client=client, **config)

    def __init__(
        self,
        api_key,
        root_id,
        root_type='collection',
        host='http://0.0.0.0',
        port=8180,
        client=None,
        metadata_types=['asset', 'file'],
    ):
        # type: (str, str, str, str, int, Any, List[str]) -> None
        '''
        Constructs a GirderExporter instances and creates a Girder client.

        Args:
            api_key (str): Girder API key.
            root_id (str): ID of folder or collection under which all data will
                be exported.
            root_type (str, optional): Root entity type. Default: collection.
                Options: folder, collection
            host (str, optional): Docker host URL address.
                Default: http://0.0.0.0.
            port (int, optional): Docker host port. Default: 8180.
            client (object, optional): Client instance, for testing.
                Default: None.
            metadata_types (list[str], optional): Metadata types to export.
                Default: [asset, file].
    ):

        Raises:
            DataError: If config is invalid.
        '''
        # sudo ip addr show docker0 | grep inet | grep docker0 | awk '{print $2}' | sed 's/\/.*//'
        # will give you the ip address of the docker network which binds to
        # localhost

        metadata_types = list(
            filter(lambda x: x in ['asset', 'file'], metadata_types)
        )
        super().__init__(metadata_types=metadata_types)

        config = dict(
            api_key=api_key,
            root_id=root_id,
            root_type=root_type,
            host=host,
            port=port,
            metadata_types=metadata_types,
        )
        config = GirderConfig(config)
        config.validate()
        config = config.to_primitive()

        self._url = f'{host}:{port}/api/v1'  # type: str

        if client is None:
            client = girder_client.GirderClient(apiUrl=self._url)  # pragma: no cover
            client.authenticate(apiKey=api_key)  # pragma: no cover
        self._client = client  # type: Any

        self._root_id = root_id  # type: str
        self._root_type = root_type  # type: str

    def _export_dirs(self, dirpath, metadata={}, exists_ok=False):
        # type: (Union[str, Path], Dict, bool) -> Dict
        '''
        Recursively export all the directories found in given path.

        Args:
            dirpath (Path or str): Directory paht to be exported.
            metadata (dict, optional): Metadata to be appended to final
                directory. Default: {}.

        Returns:
            dict: Response (contains _id key).
        '''
        dirs = Path(dirpath).parts  # type: Any
        dirs = list(filter(lambda x: x != '/', dirs))

        # if dirpath has no parents then export to root with metadata
        if len(dirs) == 1:
            return self._client.createFolder(
                self._root_id,
                dirs[0],
                metadata=metadata,
                reuseExisting=exists_ok,
                parentType=self._root_type,
            )

        # if dirpath has parents then export all parent directories
        response = dict(_id=self._root_id)
        parent_type = self._root_type
        for dir_ in dirs[:-1]:
            response = self._client.createFolder(
                response['_id'],
                dir_,
                reuseExisting=True,
                parentType=parent_type
            )
            parent_type = 'folder'

        # then export last directory with metadata
        return self._client.createFolder(
            response['_id'],
            dirs[-1],
            metadata=metadata,
            reuseExisting=exists_ok,
            parentType='folder',
        )

    def _export_content(self, metadata):
        # type: (dict) -> Any
        '''
        Export file content and metadata to Girder.
        Metadata must contain these fields:
            * filepath_relative
            * filename
            * filepath

        Args:
            metadata (dict): File metadata.

        Returns:
            object: Response.
        '''
        filepath = metadata['filepath_relative']
        filename = metadata['filename']
        parent_dir = Path(filepath).parent
        response = self._export_dirs(parent_dir, exists_ok=True)

        # folder error will always be raised before duplicate file conflict is
        # encountered, so don't test for duplicate files within directory

        meta = metadata
        if 'file' not in self._metadata_types:
            meta = {}

        response = self._client.createItem(
            response['_id'],
            filename,
            metadata=meta,
            reuseExisting=True,
        )
        response = self._client\
            .uploadFileToItem(response['_id'], metadata['filepath'])
        return response

    def _export_asset(self, metadata):
        # type: (dict) -> None
        '''
        Export asset metadata to Girder.
        Metadata must contain these fields:
            * asset_type
            * asset_path_relative

        Args:
            metadata (dict): Asset metadata.
        '''
        if metadata['asset_type'] != 'file':
            self._export_dirs(
                metadata['asset_path_relative'],
                metadata=metadata,
                exists_ok=True,
            )

    def _export_file(self, metadata):
        # type: (dict) -> None
        '''
        Exports content from file metadata in hidebound/metadata/file.

        Args:
            metadata (dict): File metadata.
        '''
        pass  # pragma: no cover

    def _export_asset_chunk(self, metadata):
        # type: (List[dict]) -> None
        '''
        Exports content from asset log in hidebound/metadata/asset-chunk.

        Args:
            metadata (list[dict]): Asset metadata chunk.
        '''
        pass  # pragma: no cover

    def _export_file_chunk(self, metadata):
        # type: (List[dict]) -> None
        '''
        Exports content from file log in hidebound/metadata/file-chunk.

        Args:
            metadata (list[dict]): File metadata chunk.
        '''
        pass  # pragma: no cover
