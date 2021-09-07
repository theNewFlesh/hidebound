from typing import Any, Dict, Optional, Tuple, Union

from collections import defaultdict
from datetime import datetime
from pathlib import Path
import json
import re
import uuid

from pandas import DataFrame
from schematics.exceptions import ValidationError
import lunchbox.tools as lbt
import numpy as np

from hidebound.core.parser import AssetNameParser
from hidebound.core.specification_base import SpecificationBase
import hidebound.core.tools as tools
# ------------------------------------------------------------------------------


'''
A library of tools for Database to use in construction of its central DataFrame.
'''


def _add_specification(data, specifications):
    # type: (DataFrame, Dict[str, SpecificationBase]) -> None
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
        # type: (str) -> Dict
        output = lbt.try_(
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


def _validate_filepath(data):
    # type: (DataFrame) -> None
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


def _add_file_traits(data):
    # type: (DataFrame) -> None
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


def _add_asset_traits(data):
    # type: (DataFrame) -> None
    '''
    Adds traits derived from aggregation of file traits.
    Add asset_traits column and one column per traits key.

    Args:
        data (DataFrame): DataFrame.
    '''
    cols = ['asset_path', 'file_traits']
    lut = data[cols].groupby('asset_path', as_index=False)\
        .agg(lambda x: tools.to_prototype(x.tolist()))\
        .apply(lambda x: x.tolist(), axis=1)\
        .tolist()
    lut = defaultdict(lambda: {}, lut)

    data['asset_traits'] = data.asset_path.apply(lambda x: lut[x])


def _validate_assets(data):
    # type: (DataFrame) -> None
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
            lambda y: lbt.try_(
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


def _add_asset_id(data):
    # type: (DataFrame) -> None
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


def _add_asset_name(data):
    # type: (DataFrame) -> None
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


def _add_asset_path(data):
    # type: (DataFrame) -> None
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
        mask = data.filepath.apply(lambda x: path.absolute().as_posix() in x)
        data.loc[mask, 'asset_path'] = path


def _add_relative_path(data, column, root_dir):
    # type: (DataFrame, str, Union[str, Path]) -> None
    '''
    Adds relative path column derived from given column.

    Args:
        data (DataFrame): DataFrame.
        column (str): Column to be made relative.
        root_dir (Path or str): Root path to be removed.
    '''
    root_dir = Path(root_dir).as_posix()
    if not root_dir.endswith('/'):
        root_dir += '/'
    mask = data[column].notnull()
    col = column + '_relative'
    data[col] = np.nan
    data.loc[mask, col] = data.loc[mask, column]\
        .apply(lambda x: re.sub(root_dir, '', Path(x).as_posix()))


def _add_asset_type(data):
    # type: (DataFrame) -> None
    '''
    Adds asset_type column derived from specification.

    Args:
        data (DataFrame): DataFrame.
    '''
    mask = data.specification_class.notnull()
    data['asset_type'] = np.nan
    data.loc[mask, 'asset_type'] = data.loc[mask, 'specification_class']\
        .apply(lambda x: x.asset_type)


def _cleanup(data):
    # type: (DataFrame) -> DataFrame
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


def _get_data_for_write(
    data,        # type: DataFrame
    source_dir,  # type: Union[str, Path]
    target_dir,  # type: Union[str, Path]
):               # type: (...) -> Optional[Tuple[DataFrame, DataFrame, DataFrame, DataFrame, DataFrame]]  # noqa: E501
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
        * Asset log - For writing asset log to a target json file.
        * File log - For writing file log to a target json file.

    Returns:
        tuple[DataFrame]: file_data, asset_metadata, file_metadata, asset_log,
            file_log.
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
    log_dir = Path(target_dir, 'logs').absolute().as_posix()

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
    for i, row in asset_meta.iterrows():
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
        item['asset_path'] = Path(
            data_dir, item['asset_path_relative']
        ).as_posix()

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

    # create asset log
    now = datetime.now().strftime('%Y-%m-%dT-%H-%M-%S')
    asset_log = DataFrame()
    asset_log['target'] = [Path(
        log_dir, 'asset', f'hidebound-asset-log_{now}.json'
    ).as_posix()]
    log = asset_meta.metadata.apply(json.dumps).tolist()
    asset_log['metadata'] = ['[\n' + ',\n'.join(log) + '\n]']

    # create file log
    file_log = DataFrame()
    file_log['target'] = [Path(
        log_dir, 'file', f'hidebound-file-log_{now}.json'
    ).as_posix()]
    log = file_meta.metadata.apply(json.dumps).tolist()
    file_log['metadata'] = ['[\n' + ',\n'.join(log) + '\n]']

    return file_data, asset_meta, file_meta, asset_log, file_log
