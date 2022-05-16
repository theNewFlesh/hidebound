from typing import Any, Callable, Dict, Generator, List, Union

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from pprint import pformat
import json
import os
import re
import shutil

from pandas import DataFrame
from schematics.exceptions import DataError, ValidationError
import dask.dataframe as dd
import jsoncomment as jsonc
import OpenEXR as openexr
# ------------------------------------------------------------------------------


'''
The tools module contains general functions useful to other hidebound modules.
'''


def list_all_files(directory, include_regex='', exclude_regex=''):
    # type: (Union[str, Path], str, str) -> Generator[Path, None, None]
    '''
    Recusively list all files within a given directory.

    Args:
        directory (str or Path): Directory to walk.
        include_regex (str, optional): Include filenames that match this regex.
            Default: ''.
        exclude_regex (str, optional): Exclude filenames that match this regex.
            Default: ''.

    Raises:
        FileNotFoundError: If argument is not a directory or does not exist.

    Yields:
        Path: File.
    '''
    directory = Path(directory)
    if not directory.is_dir():
        msg = f'{directory} is not a directory or does not exist.'
        raise FileNotFoundError(msg)

    include_re = re.compile(include_regex)
    exclude_re = re.compile(exclude_regex)

    for root, _, files in os.walk(directory):
        for file_ in files:
            filepath = Path(root, file_)

            output = True
            temp = filepath.absolute().as_posix()
            if include_regex != '' and not include_re.search(temp):
                output = False
            if exclude_regex != '' and exclude_re.search(temp):
                output = False

            if output:
                yield Path(root, file_)


def delete_empty_directories(directory):
    # type: (Union[str, Path]) -> None
    '''
    Recurses given directory tree and deletes directories that do not contain
    files or directories trees with files. .DS_Store files do not count as
    files. Does not delete given directory.

    Args:
        directory (str or Path): Directory to recurse.

    Raises:
        EnforceError: If argument is not a directory or does not exist.
    '''
    dir_ = Path(directory).as_posix()
    if not Path(dir_).is_dir():
        msg = f'{dir_} is not a directory or does not exist.'
        raise FileNotFoundError(msg)

    empty = [[], ['.DS_Store']]
    paths = []
    for root, _, files in os.walk(directory):
        if files in empty:
            paths.append(root)

    if dir_ in paths:
        paths.remove(dir_)

    for path in reversed(paths):
        if os.listdir(path) in empty:
            shutil.rmtree(path)


def directory_to_dataframe(directory, include_regex='', exclude_regex=r'\.DS_Store'):
    # type: (Union[str, Path], str, str) -> DataFrame
    r'''
    Recursively list files with in a given directory as rows in a DataFrame.

    Args:
        directory (str or Path): Directory to walk.
        include_regex (str, optional): Include filenames that match this regex.
            Default: None.
        exclude_regex (str, optional): Exclude filenames that match this regex.
            Default: '\.DS_Store'.

    Returns:
        DataFrame: DataFrame with one file per row.
    '''
    files = list_all_files(
        directory,
        include_regex=include_regex,
        exclude_regex=exclude_regex
    )  # type: Any
    files = sorted(list(files))

    data = DataFrame()
    data['filepath'] = files
    data['filename'] = data.filepath.apply(lambda x: x.name)
    data['extension'] = data.filepath \
        .apply(lambda x: os.path.splitext(x)[-1].lstrip('.'))
    data.filepath = data.filepath.apply(lambda x: x.absolute().as_posix())
    return data


def error_to_string(error):
    # type: (Exception) -> str
    '''
    Formats error as string.

    Args:
        error (Exception): Error.

    Returns:
        str: Error message.
    '''
    output = error.args[0]
    if isinstance(error, DataError):
        output = '\n' + pformat(dict(output)) + '\n'
    elif isinstance(error, ValidationError):
        output = [x.summary for x in output]
        if len(output) == 1:
            output = f' {output} '
        else:
            output = '\n' + '\n'.join(output) + '\n'
    else:
        output = f' {output} '
    output = f'{error.__class__.__name__}({output})'
    return output


def to_prototype(dicts):
    # type: (List[Dict]) -> Dict
    '''
    Converts a list of dicts into a dict of lists.
    .. example::
        :nowrap:

        >>> dicts = [dict(a=1, b=2, c=3), dict(a=10, b=20)]
        >>> to_prototype(dicts)
        {'a': [1, 10], 'b': [2, 20], 'c': [3]}

    Args:
        dicts (list[dict]): List of dicts.

    Returns:
        dict: Prototype dictionary.
    '''
    output = defaultdict(lambda: [])  # type: Any
    for dict_ in dicts:
        for key, val in dict_.items():
            output[key].append(val)
    output = dict(output)
    return output


def read_exr_header(fullpath):
    # type: (Union[str, Path]) -> dict
    '''
    Reads an OpenEXR image file header.

    Args:
        fullpath (str or Path): Image file path.

    Raises:
        IOError: If given filepath is not an EXR file.

    Returns:
        dict: EXR header.
    '''
    fullpath = Path(fullpath).absolute().as_posix()
    if not openexr.isOpenExrFile(fullpath):
        msg = f'{fullpath} is not an EXR file.'
        raise IOError(msg)

    img = openexr.InputFile(fullpath)
    return img.header()


def time_string():
    # type: () -> str
    '''
    Returns:
        str: String representing current time.
    '''
    return datetime.now().strftime('%Y-%m-%dT-%H-%M-%S')


def write_json(data, filepath):
    # type: (object, Union[Path, str]) -> None
    '''
    Convenience function for writing objects to JSON files.
    Writes lists with 1 item per line.

    Args:
        data (object): Object to be written.
        filepath (Path or str): Filepath.
    '''
    if isinstance(data, list):
        with open(filepath, 'w') as f:
            f.write('[\n')
            f.write(',\n'.join(map(json.dumps, data)))
            f.write('\n]')
    else:
        with open(filepath, 'w') as f:
            json.dump(data, f)


def read_json(filepath):
    # type (Union[Path, str]) -> object
    '''
    Convenience function for reading JSON files.
    Files may include comments.

    Args:
        filepath (Path or str): Filepath.

    Raises:
        JSONDecodeError: If no JSON data could be decoded.

    Returns:
        object: JSON object.
    '''
    output = jsonc.JsonComment().loadf(filepath)
    if output is None:
        msg = f'No JSON data could be decoded from {filepath}. '
        msg += 'Please remove any inline comments.'
        raise json.JSONDecodeError(msg, '', 0)
    return output


def pred_combinator(
    data,                   # type: Union[dd.DataFrame, dd.Series]
    predicate,              # type: Callable[[Any], bool]
    true_func,              # type: Callable[[Any], Any]
    false_func,             # type: Callable[[Any], Any]
    meta='__no_default__',  # type: Any
):
    # type: (...) -> Union[dd.DataFrame, dd.Series]
    '''
    Apply true_func to rows where predicate if true and false_func to rows where
    it is false.

    Args:
        data (DataFrame): DataFrame or Series.
        predicate (function): Function that expects a row and returns a bool.
        true_func (function): Function that expects a row. Called when predicate
            is true.
        false_func (function): Function that expects a row. Called when predicate
            is false.
        meta (object, optional): Metadata inference. Default: '__no_default__'.

    Returns:
        dd.DataFrame or dd.Series: Apply results.
    '''
    if isinstance(data, dd.DataFrame):
        return data.apply(
            lambda x: true_func(x) if predicate(x) else false_func(x),
            axis=1,
            meta=meta,
        )
    return data.apply(
        lambda x: true_func(x) if predicate(x) else false_func(x),
        meta=meta,
    )


def get_lut(data, column, aggregator, meta='__no_default__'):
    # type: (dd.DataFrame, str, Callable[[dd.DataFrame], Any], Any) -> dd.DataFrame
    '''
    Constructs a lookup table with the given column as its keys and the
    aggregator results as its values.
    Data is grouped by given column and the given aggregator is applied to each
    group of values.

    Args:
        data (dd.DataFrame): Dask DataFrame.
        column (str): Column to be used as the key.
        aggregator (function): Function that expects a group DataFrame and
            returns a scalar.
        meta (object, optional): Metadata inference. Default: '__no_default__'.

    Returns:
        dd.DataFrame: Dask DataFrame with key and value columns.
    '''
    kwargs = {}
    if meta != '__no_default__':
        kwargs['meta'] = ('value', meta)

    grp = data.groupby(column)
    keys = grp[column].first().to_frame(name='key')
    vals = grp.apply(aggregator, **kwargs).to_frame(name='value')
    lut = dd.merge(keys, vals).reset_index(drop=True)
    return lut


def lut_combinator(
    data, key_column, value_column, aggregator, meta='__no_default__'
):
    # type: (dd.DataFrame, str, str, Callable[[dd.DataFrame], Any], Any) -> dd.DataFrame
    '''
    Constructs a lookup table from given key_column, then applies it to given
    data as value column.

    Args:
        data (dd.DataFrame): Dask DataFrame.
        key_column (str): Column to be used as the lut keys.
        value_column (str): Column to be used as the values.
        aggregator (function): Function that expects a DataFrame.
        meta (object, optional): Metadata irom_nference. Default: '__no_default__'.

    Returns:
        dd.DataFrame: Dask DataFrame with value column.
    '''
    lut = get_lut(
        data,
        key_column,
        aggregator,
        meta=meta,
    )
    lut.columns = [key_column, value_column]
    data = dd.merge(data, lut, on=key_column, how='left')
    return data
