from typing import Any, Dict, Generator, List, Union

from collections import defaultdict
from pathlib import Path
from pprint import pformat
import os
import re
import shutil

import OpenEXR as openexr
from schematics.exceptions import DataError, ValidationError

from pandas import DataFrame
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
    data['extension'] = data.filepath.apply(lambda x: os.path.splitext(x)[-1][1:])
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
