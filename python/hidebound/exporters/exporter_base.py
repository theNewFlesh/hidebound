from typing import Dict, List, Optional, Union

from pathlib import Path
from schematics import Model
from schematics.types import ListType, StringType
import re

from hidebound.core.logging import DummyLogger, ProgressLogger
import hidebound.core.tools as hbt
import hidebound.core.validators as vd
# ------------------------------------------------------------------------------


class ExporterConfigBase(Model):
    '''
    A class for validating configurations supplied to S3Exporter.

    Attributes:
        metadata_types (list, optional): List of metadata types for export.
            Default: [asset, file, asset-chunk, file-chunk].
    '''
    metadata_types = ListType(
        StringType(validators=[vd.is_metadata_type]),
        required=True,
        default=['asset', 'file', 'asset-chunk', 'file-chunk']
    )


class ExporterBase:
    '''
    Abstract base class for hidebound exporters.
    '''
    def __init__(
        self, metadata_types=['asset', 'file', 'asset-chunk', 'file-chunk']
    ):
        # type: (List[str]) -> None
        '''
        Constructs a ExporterBase instance.

        Args:
            metadata_types (list[st], optional). Metadata types to be exported.
                Default: [asset, file, asset-chunk, file-chunk].
        '''
        self._metadata_types = metadata_types

    def _enforce_directory_structure(self, hidebound_dir):
        # type: (Union[str, Path]) -> None
        '''
        Ensure the following directory exist under given hidebound directory.
            * content
            * metadata
            * metadata/asset
            * metadata/file
            * metadata/asset-chunk
            * metadata/file-chunk

        Args:
            hidebound_dir (Path or str): Hidebound directory.

        Raises:
            FileNotFoundError: If any of the directories have not been found.
        '''
        data = Path(hidebound_dir, 'content')
        meta = Path(hidebound_dir, 'metadata')
        asset_dir = Path(meta, 'asset')
        file_dir = Path(meta, 'file')
        asset_chunk = Path(meta, 'asset-chunk')
        file_chunk = Path(meta, 'file-chunk')

        paths = [data, meta, asset_dir, file_dir, asset_chunk, file_chunk]
        for path in paths:
            if not path.is_dir():
                msg = f'{path.as_posix()} directory does not exist.'
                raise FileNotFoundError(msg)

    def export(
        self,
        hidebound_dir,  # type: Union[str, Path]
        logger=None  # type: Optional[Union[DummyLogger, ProgressLogger]]
    ):
        # type: (...) -> None
        '''
        Exports data within given hidebound directory.

        Args:
            hidebound_dir (Path or str): Hidebound directory.
            logger (object, optional): Progress logger. Default: None.
        '''
        # set logger
        if not isinstance(logger, ProgressLogger):
            logger = DummyLogger()

        self._enforce_directory_structure(hidebound_dir)

        hidebound_dir = Path(hidebound_dir).as_posix()
        data = hbt.directory_to_dataframe(hidebound_dir)
        data['metadata'] = None

        total = 1 + len(self._metadata_types)

        # export content
        regex = f'{hidebound_dir}/metadata/file/'
        mask = data.filepath.apply(lambda x: re.search(regex, x)).astype(bool)
        data[mask].filepath.apply(hbt.read_json).apply(self._export_content)
        logger.info('exporter: export content', step=1, total=total)

        # export metadata
        lut = {
            'asset': self._export_asset,
            'file': self._export_file,
            'asset-chunk': self._export_asset_chunk,
            'file-chunk': self._export_file_chunk,
        }
        for i, mtype in enumerate(self._metadata_types):
            regex = f'{hidebound_dir}/metadata/{mtype}/'
            mask = data.filepath.apply(lambda x: re.search(regex, x)).astype(bool)
            data[mask].filepath.apply(hbt.read_json).apply(lut[mtype])
            logger.info(f'exporter: export {mtype}', step=i + 1, total=total)

    def _export_content(self, metadata):
        # type: (Dict) -> None
        '''
        Exports from file from hidebound/content named in metadata.
        Metadata should have filepath, filepath_relative keys.

        Args:
            metadata (dict): File metadata.

        Raises:
            NotImplementedError: If method is not implemented in subclass.
        '''
        msg = '_export_content method must be implemented in subclass.'
        raise NotImplementedError(msg)

    def _export_asset(self, metadata):
        # type: (Dict) -> None
        '''
        Exports metadata from single JSON file in hidebound/metadata/asset.

        Args:
            metadata (dict): Asset metadata.

        Raises:
            NotImplementedError: If method is not implemented in subclass.
        '''
        msg = '_export_asset method must be implemented in subclass.'
        raise NotImplementedError(msg)

    def _export_file(self, metadata):
        # type: (Dict) -> None
        '''
        Exports metadata from single JSON file in hidebound/metadata/file.

        Args:
            metadata (dict): File metadata.

        Raises:
            NotImplementedError: If method is not implemented in subclass.
        '''
        msg = '_export_file method must be implemented in subclass.'
        raise NotImplementedError(msg)

    def _export_asset_chunk(self, metadata):
        # type: (List[dict]) -> None
        '''
        Exports list of asset metadata to a single asset in
        hidebound/metadata/asset-chunk.

        Args:
            metadata (list[dict]): asset metadata.

        Raises:
            NotImplementedError: If method is not implemented in subclass.
        '''
        msg = '_export_asset_chunk method must be implemented in subclass.'
        raise NotImplementedError(msg)

    def _export_file_chunk(self, metadata):
        # type: (List[dict]) -> None
        '''
        Exports list of file metadata to a single file in
        hidebound/metadata/file-chunk.

        Args:
            metadata (list[dict]): File metadata.

        Raises:
            NotImplementedError: If method is not implemented in subclass.
        '''
        msg = '_export_file_chunk method must be implemented in subclass.'
        raise NotImplementedError(msg)
