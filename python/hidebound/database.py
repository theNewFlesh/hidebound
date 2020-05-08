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

    @staticmethod
    def from_json(filepath):
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
        hidebound_parent_dir,
        specifications=[],
        include_regex='',
        exclude_regex=r'\.DS_Store',
        extraction_mode='copy',
    ):
        r'''
        Creates an instance of Database but does not populate it with data.

        Args:
            root_dir (str or Path): Root directory to recurse.
            hidebound_parent_dir (str or Path): Directory where hidebound
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
            FileNotFoundError: If hidebound_parent_dir is not directory or
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
        root = root_dir
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
        hb_root = hidebound_parent_dir
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
        self._extraction_mode = extraction_mode
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
