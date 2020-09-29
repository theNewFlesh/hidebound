from typing import Any, Dict, List, Union

from copy import deepcopy
from importlib import import_module
from pathlib import Path
import json
import os
import shutil
import sys

from pandas import DataFrame
import pandasql
import numpy as np

from hidebound.core.config import Config
from hidebound.core.specification_base import SpecificationBase
from hidebound.exporters.girder_exporter import GirderExporter
import hidebound.core.database_tools as db_tools
import hidebound.core.tools as tools
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
            config = json.load(f)
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
    ):
        # type: (Union[str, Path], Union[str, Path], List[SpecificationBase], str, str, str, Dict[str, Any]) -> None  # noqa E501
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
                hidebound/data directory. Default: copy.
            exporters (dict, optional): Dictionary of exporter configs, where
                the key is the exporter name and the value is its config.
                Default: {}.

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
        # validate spec classes
        bad_specs = list(filter(
            lambda x: not issubclass(x, SpecificationBase), specifications
        ))
        if len(bad_specs) > 0:
            msg = 'SpecificationBase may only contain subclasses of '
            msg += f'SpecificationBase. Found: {bad_specs}.'
            raise TypeError(msg)

        # validate root dir
        root = Path(root_dir)
        if not root.is_dir():
            msg = f'{root} is not a directory or does not exist.'
            raise FileNotFoundError(msg)

        # validate write mode
        modes = ['copy', 'move']
        if write_mode not in modes:
            msg = f'Invalid write mode: {write_mode} not in {modes}.'
            raise ValueError(msg)

        # validate hidebound dir
        hb_root = Path(hidebound_dir)
        if not hb_root.is_dir():
            msg = f'{hb_root} is not a directory or does not exist.'
            raise FileNotFoundError(msg)
        if Path(hb_root).name != 'hidebound':
            msg = f'{hb_root} directory is not named hidebound.'
            raise NameError(msg)

        self._root = root
        self._hb_root = hb_root
        self._include_regex = include_regex
        self._exclude_regex = exclude_regex
        self._write_mode = write_mode
        self._specifications = {x.__name__.lower(): x for x in specifications} \
            # type: Dict[str, SpecificationBase]
        self._exporters = exporters
        self.data = None

        # needed for testing
        self.__exporter_lut = None

    def create(self):
        # type: () -> "Database"
        '''
        Extract valid assets as data and metadata within the hidebound
        directory.

        Writes:

            * file data to hb_parent/hidebound/data - under same directory structure
            * file metadata as json to hb_parent/hidebound/metadata/file
            * asset metadata as json to hb_parent/hidebound/metadata/asset

        Raises:
            RunTimeError: If data has not been initialized.

        Returns:
            Database: self.
        '''
        if self.data is None:
            msg = 'Data not initialized. Please call update.'
            raise RuntimeError(msg)

        def write_json(obj, filepath):
            with open(filepath, 'w') as f:
                json.dump(obj, f)

        temp = db_tools._get_data_for_write(
            self.data, self._root, self._hb_root
        )
        if temp is None:
            return self

        file_data, file_meta, asset_meta = temp

        # make directories
        for item in temp:
            item.target.apply(lambda x: os.makedirs(Path(x).parent, exist_ok=True))

        # write file data
        if self._write_mode == 'move':
            file_data.apply(lambda x: shutil.move(x.source, x.target), axis=1)
        else:
            file_data.apply(lambda x: shutil.copy2(x.source, x.target), axis=1)

        # write file metadata
        file_meta.apply(lambda x: write_json(x.metadata, x.target), axis=1)

        # write asset metadata
        asset_meta.apply(lambda x: write_json(x.metadata, x.target), axis=1)

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

        col = 'file_traits'
        if group_by_asset:
            col = 'asset_traits'
            data = data.groupby('asset_path', as_index=False).first()

        data[col] = data[col].apply(coordinate_to_dict)
        traits = DataFrame(data[col].tolist())

        for col in traits.columns:
            if col not in data.columns:
                data[col] = np.nan

            mask = traits[col].notnull()
            data.loc[mask, col] = traits.loc[mask, col]

        # find columns by legal type
        cols = self.data.columns.tolist()
        if len(self.data) > 0:
            cols = data.applymap(type).apply(lambda x: set(x.unique()))
            legal_cols = set([int, float, str, bool, None])
            mask = cols.apply(lambda x: x.difference(legal_cols) == set())
            cols = cols[mask].index.tolist()

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

        return data

    def update(self):
        # type: () -> "Database"
        '''
        Recurse root directory, populate self.data with its files, locate and
        validate assets.

        Returns:
            Database: self.
        '''
        data = tools.directory_to_dataframe(
            self._root,
            include_regex=self._include_regex,
            exclude_regex=self._exclude_regex
        )
        if len(data) > 0:
            db_tools._add_specification(data, self._specifications)
            db_tools._validate_filepath(data)
            db_tools._add_file_traits(data)
            db_tools._add_relative_path(data, 'filepath', self._root)
            db_tools._add_asset_name(data)
            db_tools._add_asset_path(data)
            db_tools._add_relative_path(data, 'asset_path', self._root)
            db_tools._add_asset_type(data)
            db_tools._add_asset_traits(data)
            db_tools._validate_assets(data)

        data = db_tools._cleanup(data)
        self.data = data
        return self

    def delete(self):
        # type: () -> "Database"
        '''
        Deletes hidebound/data and hidebound/metadata directories and all their
        contents.

        Returns:
            Database: self.
        '''
        data_dir = Path(self._hb_root, 'data')
        if data_dir.exists():
            shutil.rmtree(data_dir)

        meta_dir = Path(self._hb_root, 'metadata')
        if meta_dir.exists():
            shutil.rmtree(meta_dir)

        return self

    def export(self):
        # type: () -> None
        '''
        Exports all the files found in in hidebound root directory.
        '''
        # TODO: Find a nicer pattern for injecting exporters.
        lut = dict(girder=GirderExporter)

        # reassign lut for testing
        if self.__exporter_lut is not None:
            lut = self.__exporter_lut

        for key, config in self._exporters.items():
            exporter = lut[key].from_config(config)
            exporter.export(self._hb_root)

            # assign instance tp exporter_lut for testing
            if self.__exporter_lut is not None:
                self.__exporter_lut[key] = exporter

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
        return pandasql.sqldf(
            query,
            {'data': self.read(group_by_asset=group_by_asset)}
        )
