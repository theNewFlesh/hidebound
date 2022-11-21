from typing import Any, Callable, Dict, Generator, List, Union

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from pprint import pformat
import json
import os
import re
import shutil

from lunchbox.enforce import Enforce
from schematics.exceptions import DataError, ValidationError
import dask.dataframe as dd
import pandas as pd
import pyjson5 as jsonc

FilePath = Union[str, Path]
DF = Union[pd.DataFrame, dd.DataFrame]
DFS = Union[pd.DataFrame, pd.Series, dd.DataFrame, dd.Series]
# ------------------------------------------------------------------------------


'''
The tools module contains general functions useful to other hidebound modules.
'''


def traverse_directory(
    directory, include_regex='', exclude_regex='', entry_type='file'
):
    # type: (FilePath, str, str, str) -> Generator[Path, None, None]
    '''
    Recusively list all files or directories within a given directory.

    Args:
        directory (str or Path): Directory to walk.
        include_regex (str, optional): Include filenames that match this regex.
            Default: ''.
        exclude_regex (str, optional): Exclude filenames that match this regex.
            Default: ''.
        entry_type (str, optional): Kind of directory entry to return. Options
            include: file, directory. Default: file.

    Raises:
        FileNotFoundError: If argument is not a directory or does not exist.
        EnforceError: If entry_type is not file or directory.

    Yields:
        Path: File.
    '''
    etypes = ['file', 'directory']
    msg = 'Illegal entry type: {a}. Legal entry types: {b}.'
    Enforce(entry_type, 'in', etypes, message=msg)

    directory = Path(directory)
    if not directory.is_dir():
        msg = f'{directory} is not a directory or does not exist.'
        raise FileNotFoundError(msg)
    # --------------------------------------------------------------------------

    include_re = re.compile(include_regex)
    exclude_re = re.compile(exclude_regex)

    for root, dirs, items in os.walk(directory):
        if entry_type == 'directory':
            items = dirs
        for item in items:
            filepath = Path(root, item)

            output = True
            temp = filepath.absolute().as_posix()
            if include_regex != '' and not include_re.search(temp):
                output = False
            if exclude_regex != '' and exclude_re.search(temp):
                output = False

            if output:
                yield filepath


def delete_empty_directories(directory):
    # type: (FilePath) -> None
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
    # type: (FilePath, str, str) -> pd.DataFrame
    r'''
    Recursively list files with in a given directory as rows in a pd.DataFrame.

    Args:
        directory (str or Path): Directory to walk.
        include_regex (str, optional): Include filenames that match this regex.
            Default: None.
        exclude_regex (str, optional): Exclude filenames that match this regex.
            Default: '\.DS_Store'.

    Returns:
        pd.DataFrame: pd.DataFrame with one file per row.
    '''
    files = traverse_directory(
        directory,
        include_regex=include_regex,
        exclude_regex=exclude_regex
    )  # type: Any
    files = sorted(list(files))

    data = pd.DataFrame()
    data['filepath'] = files
    data['filename'] = data.filepath.apply(lambda x: x.name)
    data['extension'] = data.filepath \
        .apply(lambda x: Path(x).suffix.lstrip('.'))
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


def time_string():
    # type: () -> str
    '''
    Returns:
        str: String representing current time.
    '''
    return datetime.now().strftime('%Y-%m-%dT-%H-%M-%S')


def write_json(data, filepath):
    # type: (object, FilePath) -> None
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
    # type (FilePath) -> object
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
    with open(filepath) as f:
        try:
            output = jsonc.load(f)
        except Exception as e:
            msg = f'No JSON data could be decoded from {filepath}. {str(e)}'
            raise json.JSONDecodeError(msg, '', 0)
    return output


def get_meta_kwargs(data, meta):
    # type: (DFS, Any) -> dict
    '''
    Convenience utility for coercing the meta keyword between pandas and dask.

    Args:
        data (DataFrame or Series): Pandas or dask object.
        meta (object): Meta key word argument.

    Returns:
        dict: Appropriate keyword args.
    '''
    kwargs = {}
    if meta != '__no_default__' and data.__class__ in [dd.DataFrame, dd.Series]:
        kwargs = dict(meta=meta)
    return kwargs


def pred_combinator(
    data,                   # type: DFS
    predicate,              # type: Callable[[Any], bool]
    true_func,              # type: Callable[[Any], Any]
    false_func,             # type: Callable[[Any], Any]
    meta='__no_default__',  # type: Any
):
    # type: (...) -> DFS
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
        DataFrame or Series: Apply results.
    '''
    kwargs = get_meta_kwargs(data, meta)
    if data.__class__ in [pd.DataFrame, dd.DataFrame]:
        return data.apply(
            lambda x: true_func(x) if predicate(x) else false_func(x),
            axis=1,
            **kwargs,
        )
    return data.apply(
        lambda x: true_func(x) if predicate(x) else false_func(x),
        **kwargs,
    )


def get_lut(data, column, aggregator, meta='__no_default__'):
    # type: (DF, str, Callable[[DF], Any], Any) -> DF
    '''
    Constructs a lookup table with the given column as its keys and the
    aggregator results as its values.
    Data is grouped by given column and the given aggregator is applied to each
    group of values.

    Args:
        data (DataFrame): DataFrame.
        column (str): Column to be used as the key.
        aggregator (function): Function that expects a group DataFrame and
            returns a scalar.
        meta (object, optional): Metadata inference. Default: '__no_default__'.

    Returns:
        DataFrame: DataFrame with key and value columns.
    '''
    kwargs = get_meta_kwargs(data, ('value', meta))
    merge = pd.merge
    empty = pd.DataFrame(columns=['key', 'value'])
    if isinstance(data, dd.DataFrame):
        merge = dd.merge
        empty = dd.from_pandas(empty, npartitions=1)

    grp = data.groupby(column)
    keys = grp[column].first().to_frame(name='key')
    if len(keys) == 0:
        return empty
    vals = grp.apply(aggregator, **kwargs).to_frame(name='value')
    lut = merge(keys, vals, left_index=True, right_index=True) \
        .reset_index(drop=True)
    return lut


def lut_combinator(
    data, key_column, value_column, aggregator, meta='__no_default__'
):
    # type: (DF, str, str, Callable[[DF], Any], Any) -> DF
    '''
    Constructs a lookup table from given key_column, then applies it to given
    data as value column.

    Args:
        data (DataFrame): DataFrame.
        key_column (str): Column to be used as the lut keys.
        value_column (str): Column to be used as the values.
        aggregator (function): Function that expects a pd.DataFrame.
        meta (object, optional): Metadata irom_nference. Default: '__no_default__'.

    Returns:
        DataFrame: DataFrame with value column.
    '''
    kwargs = get_meta_kwargs(data, meta)
    merge = pd.merge
    if isinstance(data, dd.DataFrame):
        merge = dd.merge

    lut = get_lut(data, key_column, aggregator, **kwargs)
    lut.columns = [key_column, value_column]
    data = merge(data, lut, on=key_column, how='left')
    return data


def str_to_bool(string):
    # type: (str) -> bool
    '''
    Converts a string to a boolean value.

    Args:
        string (str): String to be converted.

    Returns:
        bool: Boolean
    '''
    if string.lower() == 'true':
        return True
    return False
