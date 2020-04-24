from pathlib import Path
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
        specifications,
        include_regex='',
        exclude_regex=r'\.DS_Store',
        ignore_order=False
    ):
        '''
        Creates an instance of Database but does not populate it with data.

        Args:
            root (str or Path): Root directory to recurse.
            specifications (list[Specification]): List of asset specifications.
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
        self._specifications = {x.specification: x for x in specifications}
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

        # get specification data
        spec = data.filename.apply(
            lambda x: tools.try_(
                AssetNameParser.parse_specification,
                x,
                'error'
            )
        )

        # convert spec parse errors to dict
        mask = spec.apply(lambda x: not isinstance(x, dict)).astype(bool)
        spec[mask] = spec[mask].apply(lambda x: dict(error=x))

        # flatten spec data into DataFrame
        spec = DataFrame(spec.tolist())
        if 'error' not in spec.columns:
            spec['error'] = None

        # combine spec data with file data
        data = pd.concat([data, spec], axis=1)

        # get mask of files with specs
        mask = data.specification.apply(
            lambda x: isinstance(x, str) and x in self._specifications.keys()
        )
        mask = data[mask].index

        # create meta column
        data['meta'] = None
        data.meta = data.meta.apply(lambda x: {})

        # parse filenames for metadata
        parse = lambda x: AssetNameParser(
            self._specifications[x[0]].fields
        ).parse(x[1], ignore_order=self._ignore_order)
        data.loc[mask, 'meta'] = data.loc[mask]\
            .apply(lambda x: [x.specification, x.filename], axis=1)\
            .apply(lambda x: tools.try_(parse, x, 'error'))\
            .apply(lambda x: x if isinstance(x, dict) else dict(error=x))

        # concatenate data and metadata
        meta = data.meta.tolist()
        meta = DataFrame(meta)

        cols = ['specification', 'extension', 'error']
        for col in cols:
            if col not in meta.columns:
                meta[col] = None

        # merge data and metadata and clean up error columns
        meta['err'] = meta.error
        meta.drop(columns=cols, inplace=True)
        data = pd.concat([data, meta], axis=1)
        data.loc[mask, 'error'] = data.loc[mask, 'err']

        # get asset names
        data['asset_name'] = None
        mask = data.specification.notnull()
        data.loc[mask, 'asset_name'] = data[mask]\
            .apply(lambda x: self._specifications[x.specification]\
                .filepath_to_asset_name(x.fullpath),
                axis=1
            )

        # cleanup columns
        cols = [
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
        for col in cols:
            if col not in data.columns:
                data[col] = None
        data = data[cols]

        self.data = data
        return self
