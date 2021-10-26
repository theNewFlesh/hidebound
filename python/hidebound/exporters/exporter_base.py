from typing import Dict, Optional, Tuple, Union

from pathlib import Path
import os

import jsoncomment as jsonc
from hidebound.core.logging import DummyLogger, ProgressLogger
# ------------------------------------------------------------------------------


class ExporterBase:
    '''
    Abstract base class for hidebound exporters.
    '''
    def _enforce_directory_structure(self, hidebound_dir):
        # type: (Union[str, Path]) -> None
        '''
        Ensure the following directory exist under given hidebound directory.
            * content
            * metadata
            * metadata/asset
            * metadata/file
            * logs
            * logs/asset
            * logs/file

        Args:
            hidebound_dir (Path or str): Hidebound directory.

        Raises:
            FileNotFoundError: If any of the directories have not been found.
        '''
        data = Path(hidebound_dir, 'content')
        meta = Path(hidebound_dir, 'metadata')
        asset_dir = Path(meta, 'asset')
        file_dir = Path(meta, 'file')
        logs = Path(hidebound_dir, 'logs')
        asset_log = Path(logs, 'asset')
        file_log = Path(logs, 'file')
        for path in [data, meta, asset_dir, file_dir, logs, asset_log, file_log]:
            if not path.is_dir():
                msg = f'{path.as_posix()} directory does not exist.'
                raise FileNotFoundError(msg)

    def export(self, hidebound_dir, logger=None):
        # type: (Union[str, Path], Optional[Union[DummyLogger, ProgressLogger]]) -> None
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

        asset_dir = Path(hidebound_dir, 'metadata', 'asset')
        file_dir = Path(hidebound_dir, 'metadata', 'file')

        a_total = len(os.listdir(asset_dir))
        for i, asset in enumerate(os.listdir(asset_dir)):  # type: Tuple[int, Union[str, Path]]
            # export asset
            asset = Path(asset_dir, asset)
            with open(asset) as f:
                asset_meta = jsonc.JsonComment().load(f)
            self._export_asset(asset_meta)
            logger.info(
                f'exporter: export asset metadata of {asset}',
                step=i,
                total=a_total,
            )

            # export files
            filepaths = asset_meta['file_ids']
            filepaths = [Path(file_dir, f'{x}.json') for x in filepaths]

            f_total = len(filepaths)
            for j, filepath in enumerate(filepaths):
                filepath = Path(file_dir, filepath)
                with open(filepath) as f:
                    file_meta = jsonc.JsonComment().load(f)
                self._export_file(file_meta)
                logger.info(
                    f'exporter: export files and file metadata of {asset}',
                    step=j,
                    total=f_total,
                )

        # export logs
        for k, kind in enumerate(['asset', 'file']):
            log_path = Path(hidebound_dir, 'logs', kind)
            for filename in os.listdir(log_path):
                filepath = Path(log_path, filename)
                with open(filepath) as f:
                    log = dict(filename=filepath.name, content=f.read())

                if kind == 'asset':
                    self._export_asset_log(log)
                else:
                    self._export_file_log(log)

                logger.info(
                    f'exporter: export {kind} logs', step=k, total=2,
                )

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

    def _export_asset_log(self, metadata):
        # type: (Dict[str, str]) -> None
        '''
        Exports content from asset log in hidebound/logs/asset.

        Args:
            metadata (dict): Asset log.

        Raises:
            NotImplementedError: If method is not implemented in subclass.
        '''
        msg = '_export_asset_log method must be implemented in subclass.'
        raise NotImplementedError(msg)

    def _export_file_log(self, metadata):
        # type: (Dict[str, str]) -> None
        '''
        Exports content from file log in hidebound/logs/file.

        Args:
            metadata (dict): File log.

        Raises:
            NotImplementedError: If method is not implemented in subclass.
        '''
        msg = '_export_file_log method must be implemented in subclass.'
        raise NotImplementedError(msg)
