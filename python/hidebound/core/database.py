from typing import Any, Dict, List, Union

from copy import deepcopy
from importlib import import_module
from pathlib import Path
import json
import os
import shutil
import sys

from pandas import DataFrame
import jsoncomment as jsonc
import numpy as np
import pandasql
import requests

from hidebound.core.config import Config
from hidebound.core.specification_base import SpecificationBase
from hidebound.exporters.girder_exporter import GirderExporter
from hidebound.exporters.local_disk_exporter import LocalDiskExporter
from hidebound.exporters.s3_exporter import S3Exporter
import hidebound.core.database_tools as db_tools
import hidebound.core.tools as tools
from hidebound.core.logging import ProgressLogger
# ------------------------------------------------------------------------------


class Database:
    '''
    Generates a DataFrame using the files within a given directory as rows.
    '''
    @staticmethod
    def from_config(config):
        # type: (Dict[str, Any]) -> "Database"
        '''
        Constructs a Database instance given a valid config.

        Args:
            config (dict): Dictionary that meets Config class standards.

        Raises:
            DataError: If config is invalid.

        Returns:
            Database: Database instance.
        '''
        # validate config and populate with default values
        config = deepcopy(config)
        config = Config(config)
        config.validate()
        config = config.to_primitive()

        specs = []
        for path in config['specification_files']:
            sys.path.append(path)

            filepath = Path(path)
            filename = filepath.name
            filename, _ = os.path.splitext(filename)
            module = import_module(filename, filepath)  # type: ignore

            specs.extend(module.SPECIFICATIONS)  # type: ignore

        specs = list(set(specs))
        config['specifications'] = specs

        return Database(
            config['root_directory'],
            config['hidebound_directory'],
            specifications=specs,
            include_regex=config['include_regex'],
            exclude_regex=config['exclude_regex'],
            write_mode=config['write_mode'],
            exporters=config['exporters'],
            webhooks=config['webhooks'],
        )

    @staticmethod
    def from_json(filepath):
        # type: (Union[str, Path]) -> "Database"
        '''
        Constructs a Database instance from a given json file.

        Args:
            filepath (str or Path): Filepath of json config file.

        Returns:
            Database: Database instance.
        '''
        with open(filepath) as f:
            config = jsonc.JsonComment().load(f)
        return Database.from_config(config)

    def __init__(
        self,
        root_dir,
        hidebound_dir,
        specifications=[],
        include_regex='',
        exclude_regex=r'\.DS_Store',
        write_mode='copy',
        exporters={},
        webhooks=[],
    ):
        # type: (Union[str, Path], Union[str, Path], List[SpecificationBase], str, str, str, Dict[str, Any], List[Dict]) -> None  # noqa E501
        r'''
        Creates an instance of Database but does not populate it with data.

        Args:
            root_dir (str or Path): Root directory to recurse.
            hidebound_dir (str or Path): Directory where hidebound data will be
                saved.
            specifications (list[SpecificationBase], optional): List of asset
                specifications. Default: [].
            include_regex (str, optional): Include filenames that match this
                regex. Default: None.
            exclude_regex (str, optional): Exclude filenames that match this
                regex. Default: '\.DS_Store'.
            write_mode (str, optional): How assets will be extracted to
                hidebound/content directory. Default: copy.
            exporters (dict, optional): Dictionary of exporter configs, where
                the key is the exporter name and the value is its config.
                Default: {}.
            webhooks (list[dict], optional): List of webhooks to call.
                Default: [].

        Raises:
            TypeError: If specifications contains a non-SpecificationBase
                object.
            ValueError: If write_mode not is not "copy" or "move".
            FileNotFoundError: If root is not a directory or does not exist.
            FileNotFoundError: If hidebound_dir is not directory or does not
                exist.
            NameError: If hidebound_dir is not named "hidebound".

        Returns:
            Database: Database instance.
        '''
        # validate hidebound dir
        hb_root = Path(hidebound_dir)
        if not hb_root.is_dir():
            msg = f'{hb_root} is not a directory or does not exist.'
            raise FileNotFoundError(msg)

        if Path(hb_root).name != 'hidebound':
            msg = f'{hb_root} directory is not named hidebound.'
            raise NameError(msg)

        # setup logger
        logpath = Path(hb_root, 'logs', 'progress', 'hidebound-progress.log')
        self._logger = ProgressLogger(__name__, logpath)

        # validate spec classes
        bad_specs = list(filter(
            lambda x: not issubclass(x, SpecificationBase), specifications
        ))
        if len(bad_specs) > 0:
            msg = 'SpecificationBase may only contain subclasses of '
            msg += f'SpecificationBase. Found: {bad_specs}.'
            self._logger.error(msg)
            raise TypeError(msg)

        # validate root dir
        root = Path(root_dir)
        if not root.is_dir():
            msg = f'{root} is not a directory or does not exist.'
            self._logger.error(msg)
            raise FileNotFoundError(msg)

        # validate write mode
        modes = ['copy', 'move']
        if write_mode not in modes:
            msg = f'Invalid write mode: {write_mode} not in {modes}.'
            self._logger.error(msg)
            raise ValueError(msg)

        self._root = root
        self._hb_root = hb_root
        self._include_regex = include_regex
        self._exclude_regex = exclude_regex
        self._write_mode = write_mode
        self._specifications = {x.__name__.lower(): x for x in specifications} \
            # type: Dict[str, SpecificationBase]
        self._exporters = exporters
        self._webhooks = webhooks
        self.data = None

        # needed for testing
        self.__exporter_lut = None

        self._logger.info('Database initialized')

    def create(self):
        # type: () -> "Database"
        '''
        Extract valid assets as data and metadata within the hidebound
        directory.

        Writes:

            * file content to hb_parent/hidebound/content - under same directory
                                                            structure
            * asset metadata as json to hb_parent/hidebound/metadata/asset
            * file metadata as json to hb_parent/hidebound/metadata/file
            * asset log as json to hb_parent/hidebound/logs/asset
            * file log as json to hb_parent/hidebound/logs/file

        Raises:
            RunTimeError: If data has not been initialized.

        Returns:
            Database: self.
        '''
        total = 7
        if self.data is None:
            msg = 'Data not initialized. Please call update.'
            raise RuntimeError(msg)

        def write_json(obj, filepath):
            with open(filepath, 'w') as f:
                json.dump(obj, f)

        def write_log(log, filepath):
            with open(filepath, 'w') as f:
                f.write(log)

        temp = db_tools._get_data_for_write(
            self.data, self._root, self._hb_root
        )
        self._logger.info('create: get data', step=1, total=total)
        if temp is None:
            return self

        file_data, asset_meta, file_meta, asset_log, file_log = temp

        # make directories
        for item in temp:
            item.target.apply(lambda x: os.makedirs(Path(x).parent, exist_ok=True))
        self._logger.info('create: make directories', step=2, total=total)

        # write file data
        if self._write_mode == 'move':
            file_data.apply(lambda x: shutil.move(x.source, x.target), axis=1)
            tools.delete_empty_directories(self._root)
        else:
            file_data.apply(lambda x: shutil.copy2(x.source, x.target), axis=1)
        self._logger.info('create: write file data', step=3, total=total)

        # write asset metadata
        asset_meta.apply(lambda x: write_json(x.metadata, x.target), axis=1)
        self._logger.info('create: write asset metadata', step=4, total=total)

        # write file metadata
        file_meta.apply(lambda x: write_json(x.metadata, x.target), axis=1)
        self._logger.info('create: write file metadata', step=5, total=total)

        # write asset log
        asset_log.apply(lambda x: write_log(x.metadata, x.target), axis=1)
        self._logger.info('create: write asset log', step=6, total=total)

        # write file log
        file_log.apply(lambda x: write_log(x.metadata, x.target), axis=1)
        self._logger.info('create: write file log', step=7, total=total)

        self._logger.info('create: complete', step=7, total=total)
        return self

    def read(self, group_by_asset=False):
        # type: (bool) -> "DataFrame"
        '''
        Return a DataFrame which can be easily be queried and has only cells
        with scalar values.

        Args:
            group_by_asset (bool, optional): Whether to group the data by asset.
                Default: False.

        Raises:
            RunTimeError: If data has not been initialized.

        Returns:
            DataFrame: Formatted data.
        '''
        total = 5
        if self.data is None:
            msg = 'Data not initialized. Please call update.'
            raise RuntimeError(msg)

        def coordinate_to_dict(item):
            if 'coordinate' in item.keys():
                keys = ['coordinate_x', 'coordinate_y', 'coordinate_z']
                coords = dict(zip(keys, item['coordinate']))
                del item['coordinate']
                item.update(coords)
            return item

        data = self.data.copy()
        self._logger.info('read: copy data', step=1, total=total)

        col = 'file_traits'
        if group_by_asset:
            col = 'asset_traits'
            data = data.groupby('asset_path', as_index=False).first()
            self._logger.info('read: group by asset', step=2, total=total)

        data[col] = data[col].apply(coordinate_to_dict)
        traits = DataFrame(data[col].tolist())

        for col in traits.columns:
            if col not in data.columns:
                data[col] = np.nan

            mask = traits[col].notnull()
            data.loc[mask, col] = traits.loc[mask, col]
        self._logger.info('read: filter traits', step=3, total=total)

        # find columns by legal type
        cols = self.data.columns.tolist()
        if len(self.data) > 0:
            cols = data \
                .applymap(type) \
                .apply(lambda x: x.unique().tolist())
            legal_cols = set([int, float, str, bool, None])
            cols = cols.apply(lambda x: set(x).difference(legal_cols) == set())
            cols = cols[cols].index.tolist()
            self._logger.info('read: filter legal types', step=4, total=total)

        # nicely order columns
        head_cols = [
            'project',
            'specification',
            'descriptor',
            'version',
            'coordinate_x',
            'coordinate_y',
            'coordinate_z',
            'frame',
            'extension',
            'filename',
            'filepath',
            'file_error',
            'asset_name',
            'asset_path',
            'asset_type',
            'asset_error',
            'asset_valid',
        ]
        head_cols = list(filter(lambda x: x in cols, head_cols))
        tail_cols = sorted(list(set(cols).difference(head_cols)))
        cols = head_cols + tail_cols
        data = data[cols]
        self._logger.info('read: order columns', step=5, total=total)

        self._logger.info('read: complete', step=5, total=total)
        return data

    def update(self):
        # type: () -> "Database"
        '''
        Recurse root directory, populate self.data with its files, locate and
        validate assets.

        Returns:
            Database: self.
        '''
        total = 12
        self._logger.info('update', step=0, total=total)

        exclude_re = '|'.join([self._exclude_regex, 'hidebound/logs/progress'])
        data = tools.directory_to_dataframe(
            self._root,
            include_regex=self._include_regex,
            exclude_regex=exclude_re
        )
        self._logger.info(f'update: parsed {self._root}', step=1, total=total)

        if len(data) > 0:
            db_tools._add_specification(data, self._specifications)
            self._logger.info('update: add_specification', step=2, total=total)

            db_tools._validate_filepath(data)
            self._logger.info('update: validate_filepath', step=3, total=total)

            db_tools._add_file_traits(data)
            self._logger.info('update: add_file_traits', step=4, total=total)

            db_tools._add_relative_path(data, 'filepath', self._root)
            self._logger.info('update: add_relative_path', step=5, total=total)

            db_tools._add_asset_name(data)
            self._logger.info('update: add_asset_name', step=6, total=total)

            db_tools._add_asset_path(data)
            self._logger.info('update: add_asset_path', step=7, total=total)

            db_tools._add_relative_path(data, 'asset_path', self._root)
            self._logger.info('update: add_relative_path', step=8, total=total)

            db_tools._add_asset_type(data)
            self._logger.info('update: add_asset_type', step=9, total=total)

            db_tools._add_asset_traits(data)
            self._logger.info('update: add_asset_traits', step=10, total=total)

            db_tools._validate_assets(data)
            self._logger.info('update: validate_assets', step=11, total=total)

        data = db_tools._cleanup(data)
        self.data = data

        self._logger.info('update: cleanup', step=12, total=total)
        self._logger.info('update: complete', step=12, total=total)
        return self

    def delete(self):
        # type: () -> "Database"
        '''
        Deletes hidebound/content and hidebound/metadata directories and all their
        contents.

        Returns:
            Database: self.
        '''
        total = 2
        data_dir = Path(self._hb_root, 'content')
        if data_dir.exists():
            shutil.rmtree(data_dir)
        self._logger.info('delete: data directory', step=1, total=total)

        meta_dir = Path(self._hb_root, 'metadata')
        if meta_dir.exists():
            shutil.rmtree(meta_dir)
        self._logger.info('delete: metadata directory', step=2, total=total)

        self._logger.info('delete: complete', step=2, total=total)
        return self

    def call_webhooks(self):
        # type () -> requests.Response
        '''
        Calls webhooks defined in config.

        Yields:
            requests.Response: Webhook response.
        '''
        total = len(self._webhooks)
        for i, hook in enumerate(self._webhooks):
            url = hook['url']
            headers = hook.get('headers', None)
            method = hook['method']

            kwargs = {}
            if 'data' in hook and method in ['post', 'put', 'patch']:
                kwargs['data'] = json.dumps(hook['data']).encode()

            if 'json' in hook and method == 'post':
                kwargs['json'] = hook['json']

            if 'params' in hook and method == 'get':
                kwargs['params'] = hook['params']

            method = getattr(requests, method)
            response = method(url, headers=headers, **kwargs)
            self._logger.info(f'call_webhooks: {url}', step=i, total=total)
            yield response

    def export(self):
        # type: () -> "Database"
        '''
        Exports all the files found in in hidebound root directory.
        Calls webhooks afterwards.

        Returns:
            Database: Self.
        '''
        # TODO: Find a nicer pattern for injecting exporters.
        lut = dict(
            girder=GirderExporter,
            local_disk=LocalDiskExporter,
            s3=S3Exporter,
        )  # type: Dict[str, Any]

        # reassign lut for testing
        if self.__exporter_lut is not None:
            lut = self.__exporter_lut

        # always run exporters in this order
        order = ['local_disk', 's3', 'girder']
        items = sorted(self._exporters.items(), key=lambda x: order.index(x[0]))

        total = len(items)
        for i, (key, config) in enumerate(items):
            exporter = lut[key].from_config(config)
            exporter.export(self._hb_root)
            self._logger.info('export: export item', step=i, total=total)

            # assign instance to exporter_lut for testing
            if self.__exporter_lut is not None:
                self.__exporter_lut[key] = exporter

        list(self.call_webhooks())
        self._logger.info('export: complete')
        return self

    def search(self, query, group_by_asset=False):
        # type: (str, bool) -> "DataFrame"
        '''
        Search data according to given SQL query.

        Args:
            query (str): SQL query. Make sure to use "FROM data" in query.
            group_by_asset (bool, optional): Whether to group the data by asset.
                Default: False.

        Returns:
            DataFrame: Formatted data.
        '''
        result = pandasql.sqldf(
            query,
            {'data': self.read(group_by_asset=group_by_asset)}
        )
        self._logger.info(f'search: {query}', step=1, total=1)
        self._logger.info('search: complete', step=1, total=1)
        return result
