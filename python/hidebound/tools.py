from collections import defaultdict
from itertools import dropwhile, takewhile
from pathlib import Path
from pprint import pformat
import datetime
import humanfriendly
import os
import re

from schematics.exceptions import DataError, ValidationError

from pandas import DataFrame
# ------------------------------------------------------------------------------


'''
The tools module contains general functions useful to other hidebound modules.
'''


def list_all_files(directory, include_regex='', exclude_regex=''):
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
    if not isinstance(directory, Path):
        directory = Path(directory)

    if not directory.is_dir():
        msg = f'{directory} is not a directory or does not exist.'
        raise FileNotFoundError(msg)

    include_re = re.compile(include_regex)
    exclude_re = re.compile(exclude_regex)

    for root, dirs, files in os.walk(directory):
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


def directory_to_dataframe(directory, include_regex='', exclude_regex=r'\.DS_Store'):
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
    )
    files = sorted(list(files))

    data = DataFrame()
    data['filepath'] = files
    data['filename'] = data.filepath.apply(lambda x: x.name)
    data['extension'] = data.filepath.apply(lambda x: os.path.splitext(x)[-1][1:])
    data.filepath = data.filepath.apply(lambda x: x.absolute().as_posix())
    return data


def try_(function, item, return_item='item'):
    '''
    Call given function on given item, catch any exceptions and return given
    return item.

    Args:
        function (function): Function of signature lambda x: x.
        item (object): Item used to call function.
        return_item (object, optional): Item to be returned. Default: "item".

    Returns:
        object: Original item if return_item is "item".
        Exception: If return_item is "error".
        object: Object return by function call if return_item is not "item" or
            "error".
    '''
    try:
        return function(item)
    except Exception as error:
        if return_item == 'item':
            return item
        elif return_item == 'error':
            return error
        return return_item


def relative_path(module, path):
    '''
    Resolve path given current module's file path and given suffix.

    Args:
        module (str): Always __file__ of current module.
        path (str): Path relative to __file__.

    Returns:
        Path: Resolved Path object.
    '''
    module_root = Path(module).parent
    path = Path(path).parts
    path = list(dropwhile(lambda x: x == ".", path))
    up = len(list(takewhile(lambda x: x == "..", path)))
    path = Path(*path[up:])
    root = list(module_root.parents)[up - 1]
    output = Path(root, path).absolute()

    # LOGGER.debug(
    #     f'Relative_path called with: {module} and {path}. Returned: {output}'
    # )
    return output


def error_to_string(error):
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
    output = defaultdict(lambda: [])
    for dict_ in dicts:
        for key, val in dict_.items():
            output[key].append(val)
    output = dict(output)
    return output


class StopWatch():
    '''
    StopWatch is used for timing blocks of code.
    '''
    def __init__(self):
        self._delta = None
        self._start_time = None
        self._stop_time = None

    def start(self):
        '''
        Call this method directly before the code you wish to time.
        '''
        self._stop_time = None
        self._start_time = datetime.datetime.now()

    def stop(self):
        '''
        Call this method directly after the code you wish to time.
        '''
        if self._start_time is not None:
            self._stop_time = datetime.datetime.now()

    @property
    def delta(self):
        '''
        Time delta of stop - start.
        '''
        return self._stop_time - self._start_time

    @property
    def human_readable_delta(self):
        '''
        Time delta in human readable format.
        '''
        return humanfriendly.format_timespan(self.delta.total_seconds())
