from collections import defaultdict
from importlib import import_module
from pathlib import Path
import json
import os
import re
import shutil
import sys
import uuid

import numpy as np

from hidebound.config import Config
import hidebound.database_tools as db_tools
from hidebound.specification_base import SpecificationBase
import hidebound.tools as tools
# ------------------------------------------------------------------------------


class Database:
    '''
    Generates a DataFrame using the files within a given directory as rows.
    '''
    @staticmethod
    def from_config(config):
        '''
        Constructs a Database instance given a valid config.

        Args:
            config (dict): Dictionary that meets Config class standards.

        Raises:
            DataError: If config is invalid.

        Returns:
            Database: Database instance.
        '''
        Config(config).validate()

        specs = []
        for path in config['specification_files']:
            sys.path.append(path)

            filepath = Path(path)
            filename = filepath.name
            filename, _ = os.path.splitext(filename)
            module = import_module(filename, filepath)

            specs.extend(module.SPECIFICATIONS)

        specs = list(set(specs))
        config['specifications'] = specs

        return Database(
            config['root_directory'],
            config['hidebound_parent_directory'],
            specifications=specs,
            include_regex=config['include_regex'],
            exclude_regex=config['exclude_regex'],
            extraction_mode=config['extraction_mode'],
        )

    def __init__(
        self,
        root_directory,
        hidebound_parent_directory,
        specifications=[],
        include_regex='',
        exclude_regex=r'\.DS_Store',
        extraction_mode='copy',
    ):
        r'''
        Creates an instance of Database but does not populate it with data.

        Args:
            root_directory (str or Path): Root directory to recurse.
            hidebound_parent_directory (str or Path): Directory where hidebound
                directory will be created and hidebound data saved.
            specifications (list[SpecificationBase], optional): List of asset
                specifications. Default: [].
            include_regex (str, optional): Include filenames that match this
                regex. Default: None.
            exclude_regex (str, optional): Exclude filenames that match this
                regex. Default: '\.DS_Store'.
            extraction_mode (str, optional): How assets will be extracted to
                hidebound/data directory. Default: copy.

        Raises:
            TypeError: If specifications contains a non-SpecificationBase
                object.
            ValueError: If extraction_mode not is not "copy" or "move".
            FileNotFoundError: If root is not a directory or does not exist.
            FileNotFoundError: If hidebound_parent_directory is not directory or
                does not exist.


        Returns:
            Database: Database instance.
        '''
        # validate spec classes
        bad_specs = list(filter(
            lambda x: not issubclass(x, SpecificationBase), specifications
        ))
        if len(bad_specs) > 0:
            msg = f'SpecificationBase may only contain subclasses of '
            msg += f'SpecificationBase. Found: {bad_specs}.'
            raise TypeError(msg)

        # validate root dir
        root = root_directory
        if not isinstance(root, Path):
            root = Path(root)
        if not root.is_dir():
            msg = f'{root} is not a directory or does not exist.'
            raise FileNotFoundError(msg)

        # validate extraction mode
        modes = ['copy', 'move']
        if extraction_mode not in modes:
            msg = f'Invalid extraction mode: {extraction_mode} not in {modes}.'
            raise ValueError(msg)

        # validate hidebound root dir
        hb_root = hidebound_parent_directory
        if not isinstance(hb_root, Path):
            hb_root = Path(hb_root)
        if not hb_root.is_dir():
            msg = f'{hb_root} is not a directory or does not exist.'
            raise FileNotFoundError(msg)

        # create hidebound root dir
        hb_root = Path(hb_root, 'hidebound')
        os.makedirs(hb_root, exist_ok=True)

        self._root = root
        self._hb_root = hb_root
        self._include_regex = include_regex
        self._exclude_regex = exclude_regex
        self._specifications = {x.__name__.lower(): x for x in specifications}
        self.data = None

    def update(self):
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
            db_tools._add_asset_name(data)
            db_tools._add_asset_path(data)
            db_tools._add_asset_type(data)
            db_tools._add_asset_traits(data)
            db_tools._validate_assets(data)
            # db_tools._add_asset_id(data)

        data = db_tools._cleanup(data)
        self.data = data
        return self

    def create(self):
        # get valid asset data
        data = self.data.copy()
        data = data[data.asset_valid]

        # return if there is no valid asset data
        if len(data) == 0:
            return

        def write_json(obj, filepath):
            with open(filepath, 'w') as f:
                json.dump(obj, f)

        # create data directory
        data_dir = Path(self._hb_root, 'data')
        os.makedirs(data_dir, exist_ok=True)

        # create metadata directories
        m_asset_dir = Path(self._hb_root, 'metadata', 'asset')
        os.makedirs(m_asset_dir, exist_ok=True)

        m_file_dir = Path(self._hb_root, 'metadata', 'file')
        os.makedirs(m_file_dir, exist_ok=True)

        # add asset id
        keys = data.asset_path.unique().tolist()
        vals = [str(uuid.uuid4()) for x in keys]
        lut = dict(zip(keys, vals))
        lut = defaultdict(lambda: np.nan, lut)
        data['asset_id'] = data.asset_path.apply(lambda x: lut[x])

        # write data
        data['target_data_path'] = data.filepath\
            .apply(lambda x: Path(
                re.sub(self._root.as_posix(), data_dir.as_posix(), x)
            ))

        data.target_data_path\
            .apply(lambda x: os.makedirs(x.parent, exist_ok=True))

        if self.extraction_mode == 'move':
            data.apply(
                lambda x: shutil.move(x.filepath, x.target_data_path),
                axis=1
            )
        else:
            data.apply(
                lambda x: shutil.copy2(x.filepath, x.target_data_path),
                axis=1
            )

        # write file metadata
        data['file_id'] = data.asset_name.apply(lambda x: str(uuid.uuid4()))
        data['file_metadata'] = data.apply(
            lambda x: dict(
                asset_id=x.asset_id,
                asset_path=x.asset_path,
                asset_name=x.asset_name,
                asset_type=x.asset_type,
                file_id=x.file_id,
                file_traits=x.file_traits,
                filename=x.filename,
                filepath=x.filepath,
            ),
            axis=1
        )

        data['target_file_metadata_path'] = data.file_id\
            .apply(lambda x: Path(m_file_dir, x + '.json'))

        data.apply(
            lambda x: write_json(x.file_metadata, x.target_file_metadata_path),
            axis=1
        )

        # write asset metadata
        data = data\
            .groupby('asset_id', as_index=False)\
            .agg(lambda x: [dict(
                asset_id=x.asset_id.tolist()[0],
                asset_path=x.asset_path.tolist()[0],
                asset_name=x.asset_name.tolist()[0],
                asset_traits=x.asset_traits.tolist()[0],
                asset_type=x.asset_type.tolist()[0],
                file_ids=x.file_id.tolist(),
                file_traits=x.file_traits.tolist(),
                filenames=x.filename.tolist(),
                filepaths=x.filepath.tolist(),
            )])
        data['asset_metadata'] = data.asset_name
        data = data[['asset_id', 'asset_metadata']]

        data['target_asset_metadata_path'] = data.asset_id\
            .apply(lambda x: Path(m_asset_dir, x + '.json'))

        data.apply(
            lambda x: write_json(x.asset_metadata, x.target_asset_metadata_path),
            axis=1
        )
