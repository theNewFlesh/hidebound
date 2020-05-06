from collections import defaultdict
from pathlib import Path

import numpy as np
from pandas import DataFrame
from schematics.exceptions import ValidationError

from hidebound.parser import AssetNameParser
import hidebound.tools as tools
from hidebound.specification_base import SpecificationBase
# ------------------------------------------------------------------------------


class Database:
    '''
    Generates a DataFrame using the files within a given directory as rows.
    '''
    COLUMNS = [
        'project',
        'specification',
        'descriptor',
        'version',
        'coordinate',
        'frame',
        'extension',
        'filename',
        'filepath',
        'file_error',
        'file_traits',
        'asset_name',
        'asset_path',
        'asset_type',
        'asset_traits',
        'asset_error',
        'asset_valid',
        # 'asset_id',
    ]

    def __init__(
        self,
        root,
        specifications=[],
        include_regex='',
        exclude_regex=r'\.DS_Store',
        ignore_order=False
    ):
        r'''
        Creates an instance of Database but does not populate it with data.

        Args:
            root (str or Path): Root directory to recurse.
            specifications (list[SpecificationBase], optional): List of asset
                specifications. Default: [].
            include_regex (str, optional): Include filenames that match this
                regex. Default: None.
            exclude_regex (str, optional): Exclude filenames that match this
                regex. Default: '\.DS_Store'.
            ignore_order (bool, optional): Whether to ignore the filename_ order
                in filenames. Default: False.

        Raises:
            FileNotFoundError: If root is not a directory or does not exist.
            TypeError: If specifications contains a non-SpecificationBase object.

        Returns:
            Database: Database instance.
        '''
        if not isinstance(root, Path):
            root = Path(root)
        if not root.is_dir():
            msg = f'{root} is not a directory or does not exist.'
            raise FileNotFoundError(msg)

        bad_specs = list(filter(
            lambda x: not issubclass(x, SpecificationBase), specifications
        ))
        if len(bad_specs) > 0:
            msg = f'SpecificationBase may only contain subclasses of '
            msg += f'SpecificationBase. Found: {bad_specs}.'
            raise TypeError(msg)

        self._root = root
        self._include_regex = include_regex
        self._exclude_regex = exclude_regex
        self._ignore_order = ignore_order
        self._specifications = {x.name: x for x in specifications}
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
            self._add_specification(data, self._specifications)
            self._validate_filepath(data)
            self._add_file_traits(data)
            self._add_asset_name(data)
            self._add_asset_path(data)
            self._add_asset_type(data)
            self._add_asset_traits(data)
            self._validate_assets(data)
            # self._add_asset_id(data)

        data = self._cleanup(data)
        self.data = data
        return self

    # DATA-MUNGING--------------------------------------------------------------
    @staticmethod
    def _add_specification(data, specifications):
        '''
        Adds specification data to given DataFrame.

        Columns added:

            * specification
            * specification_class
            * file_error

        Args:
            data (DataFrame): DataFrame.
            specifications (dict): Dictionary of specifications.
        '''
        def get_spec(filename):
            output = tools.try_(
                AssetNameParser.parse_specification, filename, 'error'
            )
            if not isinstance(output, dict):
                output = dict(file_error=str(output))
            for key in ['specification', 'file_error']:
                if key not in output.keys():
                    output[key] = np.nan
            return output

        spec = data.filename.apply(get_spec).tolist()
        spec = DataFrame(spec)

        # set specifications
        mask = spec.specification.notnull()
        data.loc[mask, 'specification'] = spec.loc[mask, 'specification']

        # set error
        data['file_error'] = np.nan
        mask = data.specification.apply(lambda x: x not in specifications.keys())
        error = tools.error_to_string(KeyError('Specification not found.'))
        data.loc[mask, 'file_error'] = error

        # parse errors overwrite spec not found
        mask = spec.file_error.notnull()
        data.loc[mask, 'file_error'] = spec.loc[mask, 'file_error']

        # set specification class
        mask = data.file_error.isnull()
        data['specification_class'] = np.nan
        data.loc[mask, 'specification_class'] = data.loc[mask, 'specification']\
            .apply(lambda x: specifications[x])

    @staticmethod
    def _validate_filepath(data):
        '''
        Validates filepath column of given DataFrame.
        Adds error to error column if invalid.

        Args:
            data (DataFrame): DataFrame.
        '''
        def validate(row):
            try:
                row.specification_class().validate_filepath(row.filepath)
                return np.nan
            except ValidationError as e:
                return tools.error_to_string(e)

        mask = data.file_error.isnull()
        if len(data[mask]) > 0:
            data.loc[mask, 'file_error'] = data[mask].apply(validate, axis=1)

    @staticmethod
    def _add_file_traits(data):
        '''
        Adds traits derived from file in filepath.
        Add file_traits column and one column per traits key.

        Args:
            data (DataFrame): DataFrame.
        '''
        data['file_traits'] = np.nan
        data.file_traits = data.file_traits.apply(lambda x: {})
        mask = data.specification_class.notnull()
        if len(data[mask]) > 0:
            data.loc[mask, 'file_traits'] = data[mask].apply(
                lambda x: x.specification_class().get_traits(x.filepath),
                axis=1
            )

        traits = DataFrame(data.file_traits.tolist())
        # merge data and traits
        for col in traits.columns:
            if col not in data.columns:
                data[col] = np.nan

            mask = traits[col].notnull()
            data.loc[mask, col] = traits.loc[mask, col]

    @staticmethod
    def _add_asset_traits(data):
        '''
        Adds traits derived from aggregation of file traits.
        Add asset_traits column and one column per traits key.

        Args:
            data (DataFrame): DataFrame.
        '''
        lut = data\
            .groupby('asset_path', as_index=False)\
            .file_traits.agg(lambda x: tools.to_prototype(x.tolist()))\
            .apply(lambda x: x.tolist(), axis=1)\
            .tolist()
        lut = defaultdict(lambda: {}, lut)

        data['asset_traits'] = data.asset_path.apply(lambda x: lut[x])

    @staticmethod
    def _validate_assets(data):
        '''
        Validates assets according to their specification.
        Add asset_error and asset_valid columns.

        Args:
            data (DataFrame): DataFrame.
        '''
        # create error lut
        error = data.groupby('asset_path')\
            .first()\
            .apply(
                lambda y: tools.try_(
                    lambda x: x.specification_class(x.asset_traits).validate(),
                    y,
                    'error'),
                axis=1)
        lut = dict(zip(error.index.tolist(), error.tolist()))

        # assign asset_error column
        mask = data.asset_path.apply(lambda x: x in lut.keys())
        data['asset_error'] = 'null'
        data.loc[mask, 'asset_error'] = data.loc[mask, 'asset_path']\
            .apply(lambda x: lut[x])\
            .apply(lambda x: tools.error_to_string(x) if x is not None else np.nan)

        # assign asset_valid column
        data['asset_valid'] = False
        mask = data.asset_error.isnull()
        data.loc[mask, 'asset_valid'] = True

        # cleanup asset_error
        data.asset_error = data.asset_error\
            .apply(lambda x: np.nan if x == 'null' else x)

    @staticmethod
    def _add_asset_id(data):
        '''
        Adds asset_id column derived UUID hash of asset filepath.

        Args:
            data (DataFrame): DataFrame.
        '''
        mask = data.file_error.isnull()
        data['asset_id'] = np.nan
        if len(data[mask]) > 0:
            data.loc[mask, 'asset_id'] = data.loc[mask].apply(
                lambda x: x.specification_class().get_asset_id(x.filepath),
                axis=1
            )

    @staticmethod
    def _add_asset_name(data):
        '''
        Adds asset_name column derived from filepath.

        Args:
            data (DataFrame): DataFrame.
        '''
        mask = data.file_error.isnull()
        data['asset_name'] = np.nan
        if len(data[mask]) > 0:
            data.loc[mask, 'asset_name'] = data.loc[mask].apply(
                lambda x: x.specification_class().get_asset_name(x.filepath),
                axis=1
            )

    @staticmethod
    def _add_asset_path(data):
        '''
        Adds asset_path column derived from filepath.

        Args:
            data (DataFrame): DataFrame.
        '''
        mask = data.specification_class.notnull()
        data['asset_path'] = np.nan
        if len(data[mask]) > 0:
            data.loc[mask, 'asset_path'] = data.loc[mask].apply(
                lambda x: x.specification_class().get_asset_path(x.filepath),
                axis=1
            )

        # overwrite asset_path for misnamed files within asset directory
        for path in data.asset_path.dropna().unique():
            mask = data.filepath.apply(lambda x: path.as_posix() in x)
            data.loc[mask, 'asset_path'] = path

    @staticmethod
    def _add_asset_type(data):
        '''
        Adds asset_type column derived from specification.

        Args:
            data (DataFrame): DataFrame.
        '''
        mask = data.specification_class.notnull()
        data['asset_type'] = np.nan
        data.loc[mask, 'asset_type'] = data.loc[mask, 'specification_class']\
            .apply(lambda x: x.asset_type)

    @staticmethod
    def _cleanup(data):
        '''
        Ensures only specific columns are present and in correct order and Paths
        are converted to strings.

        Args:
            data (DataFrame): DataFrame.

        Returns:
            DataFrame: Cleaned up DataFrame.
        '''
        # if no files are found return empty DataFrame
        for col in Database.COLUMNS:
            if col not in data.columns:
                data[col] = np.nan
        # use copy to avoid SettingWithCopyWarning
        # TODO: figure out a way to prevent warning without copy.
        cols = data.columns
        cols = set(cols).difference(Database.COLUMNS)
        cols = sorted(cols)
        cols = Database.COLUMNS + cols
        cols = list(filter(lambda x: x != 'specification_class', cols))
        data = data[cols].copy()

        # copy filename_error to file_error
        if 'filename_error' in data.columns:
            mask = data.filename_error.notnull()
            data.loc[mask, 'file_error'] = data.loc[mask, 'filename_error']
            del data['filename_error']

        # convert Paths to str
        for col in data.columns:
            mask = data[col].apply(lambda x: isinstance(x, Path))
            data.loc[mask, col] = data.loc[mask, col]\
                .apply(lambda x: x.absolute().as_posix())
        return data
