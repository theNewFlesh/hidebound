from typing import Dict, Union

from pathlib import Path
import os
import re
import shutil

from schematics import Model
from schematics.types import StringType

from hidebound.exporters.exporter_base import ExporterBase
import hidebound.core.tools as hbt
import hidebound.core.validators as vd
# ------------------------------------------------------------------------------


class LocalDiskConfig(Model):
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

    def __init__(self, target_directory):
        # type: (str) -> None
        '''
        Constructs a LocalDiskExporter instance.
        Creates target directory if it does not exist.

        Args:
            target_directory (str): Target directory.

        Raises:
            DataError: If config is invalid.
        '''
        config = dict(target_directory=target_directory)
        LocalDiskConfig(config).validate()
        # ----------------------------------------------------------------------

        self._target_directory = config['target_directory']
        os.makedirs(self._target_directory, exist_ok=True)

    def export(self, hidebound_dir):
        # type: (Union[str, Path]) -> None
        '''
        Exports data within given hidebound directory.

        Args:
            hidebound_dir (Path or str): Hidebound directory.
        '''
        self._enforce_directory_structure(hidebound_dir)

        hidebound_dir = Path(hidebound_dir).as_posix()
        data = hbt.directory_to_dataframe(hidebound_dir)

        # only include /content, /metadata and /logs directories
        regex = f'{hidebound_dir}/(content|metadata|logs)'
        mask = data.filepath.apply(lambda x: re.search(regex, x)).astype(bool)
        data = data[mask]

        data['target'] = data.filepath \
            .apply(lambda x: re.sub(hidebound_dir, self._target_directory, x))
        data.target.apply(lambda x: os.makedirs(Path(x).parent, exist_ok=True))
        data.apply(lambda x: shutil.copy(x.filepath, x.target), axis=1)

    def _export_asset(self, metadata):
        # type: (Dict) -> None
        '''
        Exports metadata from single JSON file in hidebound/metadata/asset.

        Args:
            metadata (dict): Asset metadata.
        '''
        pass  # pragma: no cover

    def _export_file(self, metadata):
        # type: (Dict) -> None
        '''
        Exports metadata from single JSON file in hidebound/metadata/file.

        Args:
            metadata (dict): File metadata.
        '''
        pass  # pragma: no cover

    def _export_asset_log(self, metadata):
        # type: (Dict[str, str]) -> None
        '''
        Exports content from single asset log in hidebound/logs/asset.

        Args:
            metadata (dict): File log.
        '''
        pass  # pragma: no cover

    def _export_file_log(self, metadata):
        # type: (Dict[str, str]) -> None
        '''
        Exports content from single file log in hidebound/logs/file.

        Args:
            metadata (dict): File log.
        '''
        pass  # pragma: no cover
