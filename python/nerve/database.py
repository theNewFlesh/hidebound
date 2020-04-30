from pathlib import Path

import numpy as np
from pandas import DataFrame

from nerve.parser import AssetNameParser
import nerve.tools as tools
import nerve.validators as vd
from nerve.specification_base import SpecificationBase
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
            ignore_order (bool, optional): Whether to ignore the filename_ order in
                filenames. Default: False.

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
            msg = f'SpecificationBase may only contain subclasses of SpecificationBase.'
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
            self._add_filename_data(data)
            self._add_asset_name(data)
            self._add_asset_path(data)
            self._add_asset_type(data)
            self._add_asset_id(data)

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
            * error

        Args:
            data (DataFrame): DataFrame.
            specifications (dict): Dictionary of specifications.
        '''
        def get_spec(filename):
            output = tools.try_(
                AssetNameParser.parse_specification, filename, 'error'
            )
            if not isinstance(output, dict):
                output = dict(error=output)
            for key in ['specification', 'error']:
                if key not in output.keys():
                    output[key] = np.nan
            return output

        spec = data.filename.apply(get_spec).tolist()
        spec = DataFrame(spec)

        # set specifications
        mask = spec.specification.notnull()
        data.loc[mask, 'specification'] = spec.loc[mask, 'specification']

        # set error
        data['error'] = np.nan
        mask = data.specification.apply(lambda x: x not in specifications.keys())
        data.loc[mask, 'error'] = 'Specification not found.'

        # parse errors overwrite spec not found
        mask = spec.error.notnull()
        data.loc[mask, 'error'] = spec.loc[mask, 'error']

        # set specification class
        mask = data.error.isnull()
        data['specification_class'] = np.nan
        data.loc[mask, 'specification_class'] = data.loc[mask, 'specification']\
            .apply(lambda x: specifications[x])

    @staticmethod
    def _validate_filepath(data):
        '''
        Validates fullpath column of given DataFrame.
        Adds error to error column if invalid.

        Args:
            data (DataFrame): DataFrame.
        '''
        def validate(row):
            try:
                row.specification_class().validate_filepath(row.fullpath)
                return np.nan
            except vd.ValidationError as error:
                return str(error)

        mask = data.error.isnull()
        if len(data[mask]) > 0:
            data.loc[mask, 'error'] = data[mask].apply(validate, axis=1)

    @staticmethod
    def _add_filename_data(data):
        '''
        Adds data derived from parsing valid values in filename column.
        Adds many columnns.

        Args:
            data (DataFrame): DataFrame.
        '''
        mask = data.error.isnull()
        meta = data.copy()
        meta['data'] = None
        meta.data = meta.data.apply(lambda x: {})
        if len(meta[mask]) > 0:
            meta.loc[mask, 'data'] = meta[mask].apply(
                lambda x: x.specification_class().get_filename_metadata(x.filename),
                axis=1
            )
        meta = DataFrame(meta.data.tolist())

        # merge data and metadata
        for col in meta.columns:
            if col not in data.columns:
                data[col] = np.nan

            mask = meta[col].notnull()
            data.loc[mask, col] = meta.loc[mask, col]

    @staticmethod
    def _add_asset_id(data):
        '''
        Adds asset_id column derived UUID hash of asset fullpath.

        Args:
            data (DataFrame): DataFrame.
        '''
        mask = data.error.isnull()
        data['asset_id'] = np.nan
        if len(data[mask]) > 0:
            data.loc[mask, 'asset_id'] = data.loc[mask].apply(
                lambda x: x.specification_class().get_asset_id(x.fullpath),
                axis=1
            )

    @staticmethod
    def _add_asset_name(data):
        '''
        Adds asset_name column derived from fullpath.

        Args:
            data (DataFrame): DataFrame.
        '''
        mask = data.error.isnull()
        data['asset_name'] = np.nan
        if len(data[mask]) > 0:
            data.loc[mask, 'asset_name'] = data.loc[mask].apply(
                lambda x: x.specification_class().get_asset_name(x.fullpath),
                axis=1
            )

    @staticmethod
    def _add_asset_path(data):
        '''
        Adds asset_path column derived from fullpath.

        Args:
            data (DataFrame): DataFrame.
        '''
        mask = data.specification_class.notnull()
        data['asset_path'] = np.nan
        if len(data[mask]) > 0:
            data.loc[mask, 'asset_path'] = data.loc[mask].apply(
                lambda x: x.specification_class().get_asset_path(x.fullpath),
                axis=1
            )

        # overwrite asset_path for misnamed files within asset directory
        for path in data.asset_path.dropna().unique():
            mask = data.fullpath.apply(lambda x: path.as_posix() in x)
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
        columns = [
            'project',
            'specification',
            'descriptor',
            'version',
            'coordinate',
            'frame',
            'extension',
            'filename',
            'fullpath',
            'error',
            'asset_name',
            'asset_path',
            'asset_type',
            'asset_id',
        ]
        # if no files are found return empty DataFrame
        for col in columns:
            if col not in data.columns:
                data[col] = np.nan
        # use copy to avoid SettingWithCopyWarning
        # TODO: figure out a way to prevent warning without copy.
        data = data[columns].copy()

        # convert Paths to str
        for col in data.columns:
            mask = data[col].apply(lambda x: isinstance(x, Path))
            data.loc[mask, col] = data.loc[mask, col]\
                .apply(lambda x: x.absolute().as_posix())
        return data
