from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import re
import unittest

from pandas import DataFrame, Series
from schematics.exceptions import DataError, ValidationError
from schematics.models import Model
from schematics.types import StringType
import dask.dataframe as dd
import numpy as np
import pandas as pd

import hidebound.core.tools as hbt

ENABLE_DASK_CLUSTER = False
# ------------------------------------------------------------------------------


class ToolsTests(unittest.TestCase):
    def create_files(self, root):
        filepaths = [
            'a/1.foo',
            'a/b/2.json',
            'a/b/3.txt',
            'a/b/c/4.json',
            'a/b/c/5.txt'
        ]
        filepaths = [Path(root, x) for x in filepaths]
        for filepath in filepaths:
            os.makedirs(filepath.parent, exist_ok=True)
            with open(filepath, 'w') as f:
                f.write('')
        return filepaths

    def make_file_or_dir(self, filepath):
        filepath = Path(filepath)
        if '.' in filepath.as_posix():
            os.makedirs(filepath.parent, exist_ok=True)
            with open(filepath, 'w') as f:
                f.write('test')
        else:
            os.makedirs(filepath, exist_ok=True)
    # --------------------------------------------------------------------------

    def test_error_to_string(self):
        error = KeyError('Foo')
        expected = 'KeyError( Foo )'
        result = hbt.error_to_string(error)
        self.assertEqual(result, expected)

        error = ValidationError(['foo', 'bar'])
        expected = 'ValidationError(\nfoo\nbar\n)'
        result = hbt.error_to_string(error)
        self.assertEqual(result, expected)

        class Foo(Model):
            bar = StringType(required=True)
            baz = StringType(required=True)

        try:
            Foo({}).validate()
        except DataError as e:
            result = hbt.error_to_string(e)
        expected = r'DataError\(\n.*(bar|baz).*\n.*(bar|baz).*\n\)'
        self.assertRegex(result, expected)

    def test_to_prototype(self):
        dicts = [
            dict(a=1, b=2, c=3),
            dict(a=1, b=2, d=3),
            dict(a=1, b=2, e=3),
        ]
        expected = dict(a=[1, 1, 1], b=[2, 2, 2], c=[3], d=[3], e=[3])
        result = hbt.to_prototype(dicts)
        self.assertEqual(result, expected)

    def test_list_all_files(self):
        expected = '/foo/bar is not a directory or does not exist.'
        with self.assertRaisesRegexp(FileNotFoundError, expected):
            next(hbt.list_all_files('/foo/bar'))

        expected = '/foo.bar is not a directory or does not exist.'
        with self.assertRaisesRegexp(FileNotFoundError, expected):
            next(hbt.list_all_files('/foo.bar'))

        with TemporaryDirectory() as root:
            expected = sorted(self.create_files(root))
            result = sorted(list(hbt.list_all_files(root)))
            self.assertEqual(result, expected)

    def test_list_all_files_include(self):
        with TemporaryDirectory() as root:
            regex = r'\.txt'

            self.create_files(root)
            expected = [
                Path(root, 'a/b/3.txt'),
                Path(root, 'a/b/c/5.txt'),
            ]

            result = hbt.list_all_files(root, include_regex=regex)
            result = sorted(list(result))
            self.assertEqual(result, expected)

    def test_list_all_files_exclude(self):
        with TemporaryDirectory() as root:
            regex = r'\.txt'

            self.create_files(root)
            expected = [
                Path(root, 'a/1.foo'),
                Path(root, 'a/b/2.json'),
                Path(root, 'a/b/c/4.json'),
            ]

            result = hbt.list_all_files(root, exclude_regex=regex)
            result = sorted(list(result))
            self.assertEqual(result, expected)

    def test_list_all_files_include_exclude(self):
        with TemporaryDirectory() as root:
            i_regex = r'/a/b'
            e_regex = r'\.json'

            self.create_files(root)
            expected = [
                Path(root, 'a/b/3.txt'),
                Path(root, 'a/b/c/5.txt'),
            ]

            result = hbt.list_all_files(
                root,
                include_regex=i_regex,
                exclude_regex=e_regex
            )
            result = sorted(list(result))
            self.assertEqual(result, expected)

    def test_delete_empty_directories(self):
        with TemporaryDirectory() as root:
            paths = [
                Path(root, 'a0/b0/c0/l0.txt'),
                Path(root, 'a0/b0/c1'),
                Path(root, 'a0/b0/c2/.DS_Store'),
                Path(root, 'a0/b0/c3/.DS_Store'),
                Path(root, 'a0/b0/c3/d0/e0/l1.txt'),
                Path(root, 'a0/b0/c3/d1/e0'),
                Path(root, 'a0/b0/c4/d1/e0/l2.txt'),
                Path(root, 'a0/b0/c4/d2'),
                Path(root, 'a0/b0/c4/d3/e0/l3.txt'),
                Path(root, 'a0/b0/c5'),
                Path(root, 'a1/b0/c0'),
                Path(root, 'a1/b0/.DS_Store'),
                Path(root, 'a1/b1/l4.txt'),
            ]
            list(map(self.make_file_or_dir, paths))
            hbt.delete_empty_directories(root)

            result = sorted([x[0] for x in os.walk(root)])
            expected = [
                Path(root),
                Path(root, 'a0'),
                Path(root, 'a0/b0'),
                Path(root, 'a0/b0/c0'),  # parent dir of file
                Path(root, 'a0/b0/c3'),
                Path(root, 'a0/b0/c3/d0'),
                Path(root, 'a0/b0/c3/d0/e0'),  # parent dir of file
                Path(root, 'a0/b0/c4'),
                Path(root, 'a0/b0/c4/d1'),
                Path(root, 'a0/b0/c4/d1/e0'),  # parent dir of file
                Path(root, 'a0/b0/c4/d3'),
                Path(root, 'a0/b0/c4/d3/e0'),  # parent dir of file
                Path(root, 'a1'),
                Path(root, 'a1/b1'),  # parent dir of file
            ]
            expected = sorted([x.as_posix() for x in expected])
            self.assertEqual(result, expected)

    def test_delete_empty_directories_empty(self):
        with TemporaryDirectory() as root:
            hbt.delete_empty_directories(root)
            result = [x[0] for x in os.walk(root)]
            self.assertEqual(result, [root])

    def test_delete_empty_directories_errors(self):
        expected = '/foo/bar is not a directory or does not exist.'
        with self.assertRaisesRegexp(FileNotFoundError, expected):
            next(hbt.delete_empty_directories('/foo/bar'))

    def test_directory_to_dataframe(self):
        with TemporaryDirectory() as root:
            self.create_files(root)
            filepaths = [
                Path(root, 'a/b/3.txt'),
                Path(root, 'a/b/c/5.txt'),
            ]
            expected = DataFrame()
            expected['filepath'] = filepaths
            expected['filename'] = expected.filepath.apply(lambda x: x.name)
            expected['extension'] = 'txt'
            expected.filepath = expected.filepath.apply(lambda x: x.as_posix())

            result = hbt.directory_to_dataframe(
                root,
                include_regex=r'/a/b',
                exclude_regex=r'\.json'
            )
            cols = ['filepath', 'filename', 'extension']
            for col in cols:
                self.assertEqual(result[col].tolist(), expected[col].tolist())

    def test_time_string(self):
        result = re.search(
            r'\d\d\d\d-\d\d-\d\dT-\d\d-\d\d-\d\d',
            hbt.time_string()
        )
        self.assertIsNotNone(result)

    def test_write_json(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'test.json')

            # dict
            expected = dict(a='b', c='d')
            hbt.write_json(expected, filepath)
            with open(filepath) as f:
                result = json.load(f)
            self.assertEqual(result, expected)

            # list
            expected = [
                dict(a='b', c='d'),
                dict(e='f', g='h'),
                dict(i='j', k='l'),
            ]
            hbt.write_json(expected, filepath)
            with open(filepath) as f:
                result = json.load(f)
            self.assertEqual(result, expected)

            with open(filepath) as f:
                result = f.read()
            expected = map(json.dumps, expected)
            expected = '[\n' + ',\n'.join(expected) + '\n]'
            self.assertEqual(result, expected)

    def test_read_json(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'test.json')
            with open(filepath, 'w') as f:
                f.write('''
// a comment
{
    "a": "b",
    "c": "d",
}''')

            result = hbt.read_json(filepath)
            expected = {"a": "b", "c": "d"}
            self.assertEqual(result, expected)

    def test_read_json_error(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'test.json')
            with open(filepath, 'w') as f:
                f.write('// encoding error')

            expected = 'No JSON data could be decoded from .*/test.json.'
            with self.assertRaisesRegexp(json.JSONDecodeError, expected):
                hbt.read_json(filepath)

    def test_get_meta_kwargs(self):
        # pd.DataFrame
        result = hbt.get_meta_kwargs(pd.DataFrame(), str)
        self.assertEqual(result, {})

        # pd.Series
        result = hbt.get_meta_kwargs(pd.Series(), str)
        self.assertEqual(result, {})

        # dd.DataFrame
        data = dd.from_pandas(pd.DataFrame(), chunksize=1)
        result = hbt.get_meta_kwargs(data, str)
        self.assertEqual(result, dict(meta=str))

        # dd.DataFrame no meta
        result = hbt.get_meta_kwargs(data, '__no_default__')
        self.assertEqual(result, {})

        # dd.Series
        data = dd.from_pandas(pd.Series(), chunksize=1)
        result = hbt.get_meta_kwargs(data, str)
        self.assertEqual(result, dict(meta=str))

        # dd.Series no meta
        result = hbt.get_meta_kwargs(data, '__no_default__')
        self.assertEqual(result, {})

    def test_str_to_bool(self):
        assert hbt.str_to_bool('true') is True
        assert hbt.str_to_bool('True') is True
        assert hbt.str_to_bool('TRUE') is True
        assert hbt.str_to_bool('TrUe') is True

        assert hbt.str_to_bool('false') is False
        assert hbt.str_to_bool('False') is False
        assert hbt.str_to_bool('FALSE') is False
        assert hbt.str_to_bool('any-string') is False


# PRED_COMBINATOR-----------------------------------------------------------
def test_pred_combinator_dd_dataframe(db_client):
    data = DataFrame()
    data['foo'] = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    data['bar'] = [1, 2, 3, 4, 5, 6, 2, 1, 2]
    data = dd.from_pandas(data, chunksize=3)
    result = hbt.pred_combinator(
        data,
        lambda x: (x.foo + x.bar) % 2 == 0,
        lambda x: 'even',
        lambda x: 'odd',
        meta=str,
    )
    assert isinstance(result, dd.Series)

    result = result.compute().tolist()
    expected = ['even'] * 6 + ['odd'] * 3
    assert result == expected


def test_pred_combinator_dd_dataframe_nan(db_client):
    # no meta
    data = DataFrame()
    data['foo'] = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    data['bar'] = [1, 2, 3, 4, 5, 6, 2, 1, 2]

    expected = ['even'] * 6 + [np.nan] * 3
    expected = Series(expected).fillna('null').tolist()

    temp = dd.from_pandas(data, chunksize=3)
    result = hbt.pred_combinator(
        temp,
        lambda x: (x.foo + x.bar) % 2 == 0,
        lambda x: 'even',
        lambda x: np.nan,
    )
    result = result.compute().tolist()
    result = Series(result).fillna('null').tolist()
    assert result == expected

    # meta = str
    temp = dd.from_pandas(data, chunksize=3)
    result = hbt.pred_combinator(
        temp,
        lambda x: (x.foo + x.bar) % 2 == 0,
        lambda x: 'even',
        lambda x: np.nan,
        meta=str,
    )
    assert isinstance(result, dd.Series)

    result = result.compute().tolist()
    result = Series(result).fillna('null').tolist()
    assert result == expected


def test_pred_combinator_series(db_client):
    data = Series([2, 2, 2, 2, 3, 3, 3, 3])
    data = dd.from_pandas(data, chunksize=3)
    result = hbt.pred_combinator(
        data,
        lambda x: x % 2 == 0,
        lambda x: 'even',
        lambda x: 'odd',
        meta=str,
    )
    assert isinstance(result, dd.Series)

    result = result.compute().tolist()
    expected = ['even'] * 4 + ['odd'] * 4
    assert result == expected


def test_pred_combinator_pd_dataframe(db_client):
    data = pd.DataFrame()
    data['x'] = [1, 1, 1, 2, 2, 3]
    data['y'] = [1, 1, 1, 2, 2, 3]
    expected = [10, 10, 10, 20, 20, 20]

    result = hbt.pred_combinator(
        data, lambda x: x.x + x.y == 2, lambda x: 10, lambda x: 20,
    )
    assert result.tolist() == expected
    assert isinstance(result, pd.Series)


def test_pred_combinator_pd_series(db_client):
    data = pd.Series([1, 1, 1, 2, 2, 3])
    expected = [10, 10, 10, 20, 20, 20]

    result = hbt.pred_combinator(
        data, lambda x: x == 1, lambda x: 10, lambda x: 20,
    )
    assert result.tolist() == expected
    assert isinstance(result, pd.Series)


# GET_LUT-------------------------------------------------------------------
def test_get_lut_empty(db_client):
    data = pd.DataFrame()
    data['grp'] = [np.nan] * 6
    data['val'] = [1, 1, 1, 2, 2, 'foo']

    result = hbt.get_lut(data, 'grp', lambda x: x.val.tolist())
    assert isinstance(result, pd.DataFrame)
    assert result.shape == (0, 2)
    assert result.columns.tolist() == ['key', 'value']


def test_get_lut_pd_dataframe(db_client):
    data = pd.DataFrame()
    data['grp'] = [1, 1, 1, 2, 2, 3]
    data['val'] = [1, 1, 1, 2, 2, 'foo']

    result = hbt.get_lut(data, 'grp', lambda x: x.val.tolist())
    assert isinstance(result, pd.DataFrame)

    assert result.key.tolist() == [1, 2, 3]
    assert result.value.tolist() == [[1, 1, 1], [2, 2], ['foo']]


def test_get_lut_dd_dataframe(db_client):
    data = pd.DataFrame()
    data['grp'] = [1, 1, 1, 2, 2, 3]
    data['val'] = [1, 1, 1, 2, 2, 'foo']
    data = dd.from_pandas(data, chunksize=1)

    result = hbt.get_lut(data, 'grp', lambda x: str(x.val.tolist()), meta=str)
    assert isinstance(result, dd.DataFrame)

    result = result.compute()
    assert result.key.tolist() == [1, 2, 3]
    assert result.value.tolist() == ['[1, 1, 1]', '[2, 2]', "['foo']"]


# LUT_COMBINATOR------------------------------------------------------------
def test_lut_combinator_pd_dataframe(db_client):
    data = pd.DataFrame()
    data['grp'] = [1, 1, 1, 2, 2, 3]
    data['val'] = [1, 1, 1, 2, 2, 'foo']

    result = hbt.lut_combinator(data, 'grp', 'vals', lambda x: x.val.tolist())
    assert isinstance(result, pd.DataFrame)

    assert 'vals' in result.columns
    expected = [
        [1, 1, 1],
        [1, 1, 1],
        [1, 1, 1],
        [2, 2],
        [2, 2],
        ['foo'],
    ]
    assert result.vals.tolist() == expected


def test_lut_combinator_dd_dataframe(db_client):
    data = pd.DataFrame()
    data['grp'] = [1, 1, 1, 2, 2, 3]
    data['val'] = [1, 1, 1, 2, 2, 'foo']
    data = dd.from_pandas(data, chunksize=1)

    result = hbt.lut_combinator(
        data, 'grp', 'vals', lambda x: str(x.val.tolist()), meta=str
    )
    assert isinstance(result, dd.DataFrame)

    result = result.compute()
    assert 'vals' in result.columns
    expected = [
        '[1, 1, 1]',
        '[1, 1, 1]',
        '[1, 1, 1]',
        '[2, 2]',
        '[2, 2]',
        "['foo']",
    ]
    assert result.vals.tolist() == expected
