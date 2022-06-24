from typing import Any, Dict, Optional, Tuple, Union

from collections import defaultdict
from pathlib import Path
import re
import uuid

from schematics.exceptions import DataError, ValidationError
import dask.dataframe as dd
import lunchbox.tools as lbt
import numpy as np
import pandas as pd

from hidebound.core.parser import AssetNameParser
from hidebound.core.specification_base import SpecificationBase
import hidebound.core.tools as hbt

DF = Union[pd.DataFrame, dd.DataFrame]
# ------------------------------------------------------------------------------


'''
A library of tools for Database to use in construction of its central DataFrame.
'''


def add_specification(data, specifications):
    # type: (DF, Dict[str, SpecificationBase]) -> DF
    '''
    Adds specification data to given DataFrame.

    Columns added:

        * specification
        * specification_class
        * file_error

    Args:
        data (DataFrame): DataFrame.
        specifications (dict): Dictionary of specifications.

    Returns:
        DataFrame: DataFrame with specification, specification_class and
            file_error columns.
    '''
    def get_spec(filename):
        output = lbt.try_(
            AssetNameParser.parse_specification, filename, 'error'
        )
        if isinstance(output, dict):
            return output['specification'], np.nan
        return np.nan, str(output)

    # parse filenames
    parse = data.filename.apply(get_spec)

    # set specifications
    kwargs = hbt.get_meta_kwargs(data, str)
    data['specification'] = parse.apply(lambda x: x[0], **kwargs)

    # set file errors
    data['file_error'] = parse.apply(lambda x: x[1], **kwargs)

    # add specification classes
    data['specification_class'] = data.specification.apply(
        lambda x: specifications.get(x, np.nan),
        **hbt.get_meta_kwargs(data, SpecificationBase)
    )

    # add spec not found errors to rows with no file errors
    error = hbt.error_to_string(KeyError('Specification not found.'))
    data.file_error = data.file_error.mask(
        data.file_error.isnull() & data.specification_class.isnull(),
        error
    )
    return data


def validate_filepath(data):
    # type: (DF) -> DF
    '''
    Validates filepath column of given DataFrame.
    Adds error to error column if invalid.

    Args:
        data (DataFrame): DataFrame.

    Returns:
        DataFrame: DataFrame with updated file_error columns.
    '''
    def validate(row):
        try:
            row.specification_class().validate_filepath(row.filepath)
            return np.nan
        except ValidationError as e:
            return hbt.error_to_string(e)

    data.file_error = hbt.pred_combinator(
        data,
        lambda x: pd.isnull(x.file_error),
        validate,
        lambda x: x.file_error,
    )
    return data


def add_file_traits(data):
    # type: (DF) -> DF
    '''
    Adds traits derived from file in filepath.
    Add file_traits column and one column per traits key.

    Args:
        data (DataFrame): DataFrame.

    Returns:
        DataFrame: DataFrame with updated file_error columns.
    '''
    data['file_traits'] = hbt.pred_combinator(
        data,
        lambda x: pd.notnull(x.specification_class),
        lambda x: x.specification_class().get_traits(x.filepath),
        lambda x: {},
        **hbt.get_meta_kwargs(data, dict)
    )
    return data


def add_relative_path(data, column, root_dir):
    # type: (DF, str, Union[str, Path]) -> DF
    '''
    Adds relative path column derived from given column.

    Args:
        data (DataFrame): DataFrame.
        column (str): Column to be made relative.
        root_dir (Path or str): Root path to be removed.

    Returns:
        DataFrame: DataFrame with updated [column]_relative column.
    '''
    root_dir_ = Path(root_dir).as_posix()  # type: str
    if not root_dir_.endswith('/'):
        root_dir_ += '/'
    col = column + '_relative'
    data[col] = hbt.pred_combinator(
        data[column],
        lambda x: isinstance(x, str),
        lambda x: re.sub(root_dir_, '', Path(x).as_posix()),
        lambda x: x,
        **hbt.get_meta_kwargs(data, str)
    )
    return data


def add_asset_name(data):
    # type: (DF) -> DF
    '''
    Adds asset_name column derived from filepath.

    Args:
        data (DataFrame): DataFrame.

    Returns:
        DataFrame: DataFrame with updated asset_name column.
    '''
    data['asset_name'] = hbt.pred_combinator(
        data,
        lambda x: pd.isnull(x.file_error),
        lambda x: x.specification_class().get_asset_name(x.filepath),
        lambda x: np.nan,
        **hbt.get_meta_kwargs(data, str)
    )
    return data


def add_asset_path(data):
    # type: (DF) -> DF
    '''
    Adds asset_path column derived from filepath.

    Args:
        data (DataFrame): DataFrame.

    Returns:
        DataFrame: DataFrame with asset_path column.
    '''
    data['asset_path'] = hbt.pred_combinator(
        data,
        lambda x: pd.notnull(x.specification_class),
        lambda x: x.specification_class().get_asset_path(x.filepath).as_posix(),
        lambda x: np.nan,
        **hbt.get_meta_kwargs(data, str)
    )
    return data


def add_asset_type(data):
    # type: (DF) -> DF
    '''
    Adds asset_type column derived from specification.

    Args:
        data (DataFrame): DataFrame.

    Returns:
        DataFrame: DataFrame with asset_type column.
    '''
    data['asset_type'] = hbt.pred_combinator(
        data.specification_class,
        lambda x: pd.notnull(x),
        lambda x: x.asset_type,
        lambda x: np.nan,
        **hbt.get_meta_kwargs(data, str)
    )
    return data


def add_asset_traits(data):
    # type: (DF) -> DF
    '''
    Adds traits derived from aggregation of file traits.
    Add asset_traits column and one column per traits key.

    Args:
        data (DataFrame): DataFrame.

    Returns:
        DataFrame: DataFrame with asset_traits column.
    '''
    data = hbt.lut_combinator(
        data,
        'asset_path',
        'asset_traits',
        lambda x: x.file_traits.tolist(),
        **hbt.get_meta_kwargs(data, object)
    )
    data.asset_traits = hbt.pred_combinator(
        data.asset_traits,
        lambda x: isinstance(x, list),
        hbt.to_prototype,
        lambda x: np.nan,
        **hbt.get_meta_kwargs(data, dict)
    )
    return data


def validate_assets(data):
    # type: (DF) -> DF
    '''
    Validates assets according to their specification.
    Add asset_error and asset_valid columns.

    Args:
        data (DataFrame): DataFrame.

    Returns:
        DataFrame: DataFrame with asset_error and asset_valid columns.
    '''
    def error_func(row):
        try:
            row.specification_class(row.asset_traits).validate()
        except DataError as e:
            return hbt.error_to_string(e)
        return np.nan

    # add asset error
    data['asset_error'] = hbt.pred_combinator(
        data,
        lambda x: isinstance(x.asset_traits, dict) and pd.notnull(x.specification_class),
        error_func,
        lambda x: np.nan,
        **hbt.get_meta_kwargs(data, Exception)
    )

    # assign asset_valid column
    data['asset_valid'] = hbt.pred_combinator(
        data,
        lambda x: pd.isnull(x.asset_error) and pd.isnull(x.file_error) and pd.notnull(x.specification_class),  # noqa E501
        lambda x: True,
        lambda x: False,
        **hbt.get_meta_kwargs(data, bool)
    )
    return data


def cleanup(data):
    # type: (DF) -> DF
    '''
    Ensures only specific columns are present and in correct order and Paths
    are converted to strings.

    Args:
        data (DataFrame): DataFrame.

    Returns:
        DataFrame: Cleaned up DataFrame.
    '''
    columns = [
        'specification',
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
    ]
    # if no files are found return empty DataFrame
    for col in columns:
        if col not in data.columns:
            data[col] = np.nan
    # use copy to avoid SettingWithCopyWarning
    # TODO: figure out a way to prevent warning without copy.
    cols = data.columns
    cols = set(cols).difference(columns)
    cols = sorted(cols)
    cols = columns + cols
    cols = list(filter(lambda x: x != 'specification_class', cols))
    data = data[cols].copy()

    # convert Paths to str
    for col in data.columns:
        mask = data[col].apply(lambda x: isinstance(x, Path))
        data.loc[mask, col] = data.loc[mask, col]\
            .apply(lambda x: x.absolute().as_posix())
    return data


def add_asset_id(data):
    # type: (pd.DataFrame) -> pd.DataFrame
    '''
    Adds asset_id column derived UUID hash of asset filepath.

    Args:
        data (pd.DataFrame): DataFrame.

    Returns:
        pd.DataFrame: DataFrame with asset_id column.
    '''
    mask = data.file_error.isnull()
    data['asset_id'] = np.nan
    if len(data[mask]) > 0:
        data.loc[mask, 'asset_id'] = data.loc[mask].apply(
            lambda x: x.specification_class().get_asset_id(x.filepath),
            axis=1
        )
    return data


def get_data_for_write(
    data,        # type: pd.DataFrame
    source_dir,  # type: Union[str, Path]
    target_dir,  # type: Union[str, Path]
):               # type: (...) -> Optional[Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]]  # noqa: E501
    '''
    Split given data into three DataFrame creating files.

    Args:
        data: DataFrame: DataFrame to be transformed.
        source_dir (str or Path): Source directory of asset files.
        target_dir (str or Path): Target directory where data will be written.

    DataFrames:

        * File data - For writing asset file data to a target filepath.
        * Asset metadata - For writing asset metadata to a target json file.
        * File metadata - For writing file metadata to a target json file.
        * Asset chunk - For writing asset metadata chunk to a target json file.
        * File chunk - For writing file metadata chunk to a target json file.

    Returns:
        tuple[DataFrame]: file_data, asset_metadata, file_metadata, asset_chunk,
            file_chunk.
    '''
    # TODO: flatten file_traits and flatten asset_traits
    # get valid asset data
    data = data.copy()
    data = data[data.asset_valid]

    # return if there is no valid asset data
    if len(data) == 0:
        return None

    source_dir = Path(source_dir).absolute().as_posix()
    data_dir = Path(target_dir, 'content').absolute().as_posix()
    meta_dir = Path(target_dir, 'metadata').absolute().as_posix()

    # add asset id
    keys = data.asset_path.unique().tolist()
    vals = [str(uuid.uuid4()) for x in keys]
    lut = dict(zip(keys, vals))  # type: Any
    lut = defaultdict(lambda: np.nan, lut)
    data['asset_id'] = data.asset_path.apply(lambda x: lut[x])

    # create file id and metadata
    data['file_id'] = data.asset_name.apply(lambda x: str(uuid.uuid4()))
    data['metadata'] = data.apply(
        lambda x: dict(
            asset_id=x.asset_id,
            asset_path=Path(data_dir, x.asset_path_relative).as_posix(),
            asset_path_relative=x.asset_path_relative,
            asset_name=x.asset_name,
            asset_type=x.asset_type,
            file_id=x.file_id,
            file_traits=x.file_traits,
            filename=x.filename,
            filepath=Path(data_dir, x.filepath_relative).as_posix(),
            filepath_relative=x.filepath_relative,
        ),
        axis=1
    )

    # create asset metadata
    asset_meta = data\
        .groupby('asset_id', as_index=False)\
        .agg(lambda x: x.tolist())

    meta = []
    lut = dict(
        asset_id='asset_id',
        asset_path='asset_path',
        asset_path_relative='asset_path_relative',
        asset_name='asset_name',
        asset_traits='asset_traits',
        asset_type='asset_type',
        file_id='file_ids',
        file_traits='file_traits',
        filename='filenames',
        filepath='filepaths',
        filepath_relative='filepaths_relative',
    )
    keys = asset_meta.columns.tolist()
    for _, row in asset_meta.iterrows():
        vals = row.tolist()
        item = dict(zip(keys, vals))
        item = {lut[k]: item[k] for k in lut.keys()}

        # grab the first occurence of these columns
        cols = [
            'asset_name',
            'asset_path',
            'asset_path_relative',
            'asset_type',
            'asset_traits'
        ]
        for col in cols:
            item[col] = item[col][0]
        del item['file_traits']

        # replace asset root
        item['asset_path'] = Path(data_dir, item['asset_path_relative']) \
            .as_posix()

        meta.append(item)
    asset_meta['metadata'] = meta

    asset_meta['target'] = asset_meta.asset_id\
        .apply(lambda x: Path(meta_dir, 'asset', x + '.json').as_posix())
    asset_meta = asset_meta[['metadata', 'target']]

    # create file data
    file_data = data.copy()
    file_data['source'] = file_data.filepath
    file_data['target'] = file_data.source\
        .apply(lambda x: re.sub(source_dir, data_dir, x))
    file_data = file_data[['source', 'target']]

    # create file metadata
    file_meta = data.copy()
    file_meta['target'] = file_meta.file_id\
        .apply(lambda x: Path(meta_dir, 'file', x + '.json').as_posix())
    file_meta = file_meta[['metadata', 'target']]

    # get time
    now = hbt.time_string()

    # create asset chunk
    asset_chunk = pd.DataFrame()
    asset_chunk['metadata'] = [asset_meta.metadata.tolist()]
    asset_chunk['target'] = [Path(
        meta_dir, 'asset-chunk', f'hidebound-asset-chunk_{now}.json'
    ).as_posix()]

    # create file chunk
    file_chunk = pd.DataFrame()
    file_chunk['metadata'] = [file_meta.metadata.tolist()]
    file_chunk['target'] = [Path(
        meta_dir, 'file-chunk', f'hidebound-file-chunk_{now}.json'
    ).as_posix()]

    return file_data, asset_meta, file_meta, asset_chunk, file_chunk
