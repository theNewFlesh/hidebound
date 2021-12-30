from typing import Dict, List

from pathlib import Path
import os
import shutil

from schematics.types import StringType

from hidebound.exporters.exporter_base import ExporterBase, ExporterConfigBase
import hidebound.core.tools as hbt
import hidebound.core.validators as vd
# ------------------------------------------------------------------------------


class LocalDiskConfig(ExporterConfigBase):
    '''
    A class for validating configurations supplied to LocalDiskExporter.

    Attributes:
        target_directory (str): Target directory.
    '''
    target_directory = StringType(
        required=True, validators=[vd.is_legal_directory]
    )  # type: StringType


class LocalDiskExporter(ExporterBase):
    @staticmethod
    def from_config(config):
        # type: (Dict) -> LocalDiskExporter
        '''
        Construct a LocalDiskExporter from a given config.

        Args:
            config (dict): Config dictionary.

        Raises:
            DataError: If config is invalid.

        Returns:
            LocalDiskExporter: LocalDiskExporter instance.
        '''
        return LocalDiskExporter(**config)

    def __init__(
        self,
        target_directory,
        metadata_types=['asset', 'file', 'asset-chunk', 'file-chunk'],
    ):
        # type: (str, List[str]) -> None
        '''
        Constructs a LocalDiskExporter instance.
        Creates target directory if it does not exist.

        Args:
            target_directory (str): Target directory.

        Raises:
            DataError: If config is invalid.
        '''
        super().__init__(metadata_types=metadata_types)

        config = dict(
            target_directory=target_directory,
            metadata_types=metadata_types,
        )
        LocalDiskConfig(config).validate()
        # ----------------------------------------------------------------------

        self._target_directory = str(config['target_directory'])  # type: str
        os.makedirs(self._target_directory, exist_ok=True)

    def _export_content(self, metadata):
        # type: (Dict) -> None
        '''
        Exports content from filepath in given metadata.

        Args:
            metadata (dict): File metadata.
        '''
        source = metadata['filepath']
        target = Path(
            self._target_directory,
            'content',
            metadata['filepath_relative'],
        )
        os.makedirs(Path(target).parent, exist_ok=True)
        shutil.copy(source, target)

    def _export_asset(self, metadata):
        # type: (Dict) -> None
        '''
        Exports metadata from single JSON file in hidebound/metadata/asset.

        Args:
            metadata (dict): Asset metadata.
        '''
        target = Path(
            self._target_directory,
            'metadata',
            'asset',
            metadata['asset_id'] + '.json',
        )
        os.makedirs(Path(target).parent, exist_ok=True)
        hbt.write_json(metadata, target)

    def _export_file(self, metadata):
        # type: (Dict) -> None
        '''
        Exports metadata from single JSON file in hidebound/metadata/file.

        Args:
            metadata (dict): File metadata.
        '''
        target = Path(
            self._target_directory,
            'metadata',
            'file',
            metadata['file_id'] + '.json',
        )
        os.makedirs(Path(target).parent, exist_ok=True)
        hbt.write_json(metadata, target)

    def _export_asset_chunk(self, metadata):
        # type: (List[dict]) -> None
        '''
        Exports content from single asset chunk in hidebound/metadata/asset-chunk.

        Args:
            metadata (list[dict]): Asset metadata.
        '''
        now = hbt.time_string()
        target = Path(
            self._target_directory,
            'metadata',
            'asset-chunk',
            f'hidebound-asset-chunk_{now}.json',
        )
        os.makedirs(Path(target).parent, exist_ok=True)
        hbt.write_json(metadata, target)

    def _export_file_chunk(self, metadata):
        # type: (List[dict]) -> None
        '''
        Exports content from single file chunk in hidebound/metadata/file-chunk.

        Args:
            metadata (list[dict]): File metadata.
        '''
        now = hbt.time_string()
        target = Path(
            self._target_directory,
            'metadata',
            'file-chunk',
            f'hidebound-file-chunk_{now}.json',
        )
        os.makedirs(Path(target).parent, exist_ok=True)
        hbt.write_json(metadata, target)
