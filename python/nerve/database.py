from pathlib import Path

import numpy as np
import pandas as pd
from pandas import DataFrame

from nerve.parser import AssetNameParser
import nerve.tools as tools
from nerve.specification_base import Specification
# ------------------------------------------------------------------------------


class Database:
    '''
    Generates a DataFrame using the files within a given directory as rows.
    '''
    def __init__(
        self,
        root,
        specifications=[],
        include_regex='',
        exclude_regex=r'\.DS_Store',
        ignore_order=False
    ):
        '''
        Creates an instance of Database but does not populate it with data.

        Args:
            root (str or Path): Root directory to recurse.
            specifications (list[Specification], optional): List of asset
                specifications. Default: [].
            include_regex (str, optional): Include filenames that match this
                regex. Default: None.
            exclude_regex (str, optional): Exclude filenames that match this
                regex. Default: '\.DS_Store'.
            ignore_order (bool, optional): Whether to ignore the field order in
                filenames. Default: False.

        Raises:
            FileNotFoundError: If root is not a directory or does not exist.
            TypeError: If specifications contains a non-Specification object.

        Returns:
            Database: Database instance.
        '''
        if not isinstance(root, Path):
            root = Path(root)
        if not root.is_dir():
            msg = f'{root} is not a directory or does not exist.'
            raise FileNotFoundError(msg)

        bad_specs = list(filter(
            lambda x: not issubclass(x, Specification), specifications
        ))
        if len(bad_specs) > 0:
            msg = f'Specification may only contain subclasses of Specification.'
            msg += f' Found: {bad_specs}.'
            raise TypeError(msg)

        self._root = root
        self._include_regex = include_regex
        self._exclude_regex = exclude_regex
        self._ignore_order = ignore_order
        self._specifications = {x.name: x for x in specifications}
        self.data = None

    def update(self):
        '''
        Recurse root directory and populate self.data with its files.

        Returns:
            Database: self.
        '''
        # get file data
        data = tools.directory_to_dataframe(
            self._root,
            include_regex=self._include_regex,
            exclude_regex=self._exclude_regex
        )

        # add all columns to data
        columns = [
            'project',
            'specification',
            'descriptor',
            'version',
            'coordinate',
            'frame',
            'extension',
            'asset_name',
            'filename',
            'fullpath',
            'error'
        ]
        for col in columns:
            if col not in data.columns:
                data[col] = np.nan

        # if no files are found return empty DataFrame
        if len(data) == 0:
            data.columns = columns
            self.data = data
            return self

        # get specification data------------------------------------------------
        def to_asset_spec(filename):
            output = tools.try_(
                AssetNameParser.parse_specification, filename, 'error'
            )
            if not isinstance(output, dict):
                output = dict(error=output)
            for key in ['specification', 'error']:
                if key not in output.keys():
                    output[key] = np.nan
            return output

        spec = data.filename.apply(to_asset_spec).tolist()
        spec = DataFrame(spec)

        # combine spec data with file data
        data['error'] = spec.error
        mask = spec.specification.notnull()
        data.loc[mask, 'specification'] = spec.loc[mask, 'specification']

        # get metadata----------------------------------------------------------
        def to_asset_metadata(specification, filename):
            if specification not in self._specifications.keys():
                return {}

            spec = self._specifications[specification]
            parser = AssetNameParser(spec.fields)
            output = tools.try_(parser.parse, filename, 'error')
            if not isinstance(output, dict):
                output = dict(error=output)

            for key in ['specification', 'extension', 'error']:
                if key not in output.keys():
                    output[key] = np.nan
            return output

        meta = data.apply(
            lambda x: to_asset_metadata(x.specification, x.filename),
            axis=1
        )
        meta = DataFrame(meta.tolist())

        # merge data and metadata
        for col in meta.columns:
            if col not in data.columns:
                data[col] = np.nan

            mask = meta[col].notnull()
            data.loc[mask, col] = meta.loc[mask, col]

        # get asset names
        data['asset_name'] = data.apply(
            lambda y: tools.try_(
                lambda x: self\
                    ._specifications[x.specification]\
                    .filename_to_asset_name(x.filename),
                y,
                np.nan
            ),
            axis=1
        )

        # cleanup columns
        for col in columns:
            if col not in data.columns:
                data[col] = np.nan
        data = data[columns]

        self.data = data
        return self
