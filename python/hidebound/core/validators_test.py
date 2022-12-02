from itertools import product
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from schematics.exceptions import ValidationError
from schematics.models import Model
from schematics.types import StringType
import numpy as np
import pytest

import hidebound.core.validators as vd
# ------------------------------------------------------------------------------


class ValidatorsTests(unittest.TestCase):
    # VALIDATE------------------------------------------------------------------
    def test_validate(self):
        message = '{} is not foo.'

        @vd.validate(message)
        def foo(item):
            return item == 'foo'

        foo('foo')

        expected = message.format('bar')
        with self.assertRaisesRegexp(ValidationError, expected):
            foo('bar')

        expected = message.format(1)
        with self.assertRaisesRegexp(ValidationError, expected):
            foo(1)

    def test_validate_extra_arg(self):
        message = '{} is not less than {}.'

        @vd.validate(message)
        def foo(a, b):
            return a < b

        foo(1, 2)

        expected = message.format(2, 1)
        with self.assertRaisesRegexp(ValidationError, expected):
            foo(2, 1)

    def test_validate_list(self):
        message = 'Sum of {} is not less than 4.'

        @vd.validate(message)
        def foo(items):
            return sum(items) < 4

        foo([0, 1, 2])

        expected = message.format(r'\[1, 2, 3\]')
        with self.assertRaisesRegexp(ValidationError, expected):
            foo([1, 2, 3])

        expected = message.format(1)
        with self.assertRaises(TypeError):
            foo(1)

    def test_validate_list_extra_arg(self):
        message = 'Sum of {} is not less than {}.'

        @vd.validate(message)
        def foo(a, b):
            return sum(a) < b

        foo([0, 1, 2], 4)

        expected = message.format(r'\[1, 2, 3\]', 4)
        with self.assertRaisesRegexp(ValidationError, expected):
            foo([1, 2, 3], 4)

        with self.assertRaises(TypeError):
            foo(1, 4)

    # VALIDATE_EACH-------------------------------------------------------------
    def test_validate_each(self):
        message = '{} is not foo.'

        @vd.validate_each(message)
        def foo(item):
            return item == 'foo'

        foo('foo')

        expected = message.format('bar')
        with self.assertRaisesRegexp(ValidationError, expected):
            foo('bar')

        expected = message.format(1)
        with self.assertRaisesRegexp(ValidationError, expected):
            foo(1)

    def test_validate_each_extra_arg(self):
        message = '{} is not less than {}.'

        @vd.validate_each(message)
        def foo(a, b):
            return a < b

        foo(1, 2)

        expected = message.format(2, 1)
        with self.assertRaisesRegexp(ValidationError, expected):
            foo(2, 1)

    def test_validate_each_list(self):
        message = '{} is not less than 4.'

        @vd.validate_each(message)
        def foo(item):
            return item < 4

        foo([0, 1, 2])

        expected = message.format(5)
        with self.assertRaisesRegexp(ValidationError, expected):
            foo([1, 2, 5])

        with self.assertRaises(TypeError):
            foo('a')

    def test_validate_each_list_extra_arg(self):
        message = '{} is not less than {}.'

        @vd.validate_each(message)
        def foo(a, b):
            return a < b

        foo([0, 1, 2], 4)

        expected = message.format(5, 4)
        with self.assertRaisesRegexp(ValidationError, expected):
            foo([1, 2, 5], 4)

        with self.assertRaises(TypeError):
            foo([1, 'a'], 4)
    # --------------------------------------------------------------------------

    def test_is_project(self):
        vd.is_project('proj001')

        expected = '.*proj-001.* is not a valid project name'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_project('proj-001')

        expected = '.*bigfancyproj001.* is not a valid project name'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_project('bigfancyproj001')

        expected = '.*proj00001.* is not a valid project name'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_project('proj00001')

    def test_is_descriptor(self):
        vd.is_descriptor('desc')

        expected = '.*master-desc.* is not a valid descriptor'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_descriptor('master-desc')

        expected = '.*Desc.* is not a valid descriptor'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_descriptor('Desc')

        expected = '.* is not a valid descriptor'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_descriptor('')

    def test_is_version(self):
        vd.is_version(1)

        expected = '-1 is not a valid version.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_version(-1)

        expected = '0 is not a valid version.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_version(0)

        expected = '1000 is not a valid version.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_version(1000)

    def test_is_frame(self):
        vd.is_frame(59)

        expected = '-1 is not a valid frame.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_frame(-1)

        expected = '10000 is not a valid frame.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_frame(10000)

    def test_is_coordinate(self):
        vd.is_coordinate([59])
        vd.is_coordinate([59, 0])
        vd.is_coordinate([59, 4, 23])

        expected = r'\[-1\] is not a valid coordinate\.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_coordinate([-1])

        expected = r'\[0, 2, -1\] is not a valid coordinate\.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_coordinate([0, 2, -1])

        expected = r'\[0, 0, 10000\] is not a valid coordinate\.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_coordinate([0, 0, 10000])

    def test_is_extension(self):
        vd.is_extension('png')

        expected = r'.*\$\$\$.* is not a valid extension'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_extension('$$$')

    def test_is_eq(self):
        vd.is_eq(1, 1)

        expected = 'foo != bar.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_eq('foo', 'bar')

    def test_is_lt(self):
        vd.is_lt(0, 1)

        expected = '1 !< 0.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_lt(1, 0)

    def test_is_gt(self):
        vd.is_gt(1, 0)

        expected = '0 !> 1.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_gt(0, 1)

    def test_is_lte(self):
        vd.is_lte(1, 1)

        expected = '1 !<= 0.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_lte(1, 0)

    def test_is_gte(self):
        vd.is_gte(1, 1)

        expected = '0 !>= 1.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_gte(0, 1)

    def test_is_homogenous(self):
        vd.is_homogenous([])
        vd.is_homogenous(['a'])
        vd.is_homogenous([0, 0, 0])
        vd.is_homogenous(list('aaa'))

        item = [0, 0, 1]
        with self.assertRaises(ValidationError) as e:
            vd.is_homogenous(item)
        expected = f'{item} is not homogenous.'
        self.assertIn(expected, str(e.exception[0]))

        item = [0, 0, 'a']
        with self.assertRaises(ValidationError) as e:
            vd.is_homogenous(item)
        expected = f'{item} is not homogenous.'
        self.assertIn(expected, str(e.exception[0]))

        item = [0, 0, np.nan]
        with self.assertRaises(ValidationError) as e:
            vd.is_homogenous(item)
        expected = f'{item} is not homogenous.'
        self.assertIn(expected, str(e.exception[0]))

        item = [np.nan, 0, np.nan]
        with self.assertRaises(ValidationError) as e:
            vd.is_homogenous(item)
        expected = f'{item} is not homogenous.'
        self.assertIn(expected, str(e.exception[0]))

    def test_is_in(self):
        vd.is_in(0, [0, 1, 2])
        vd.is_in(2, ['a', 1, 2])

        expected = r'0 is not in \[3, 4, 5\]'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_in(0, [3, 4, 5])

    def test_is_attribute_of(self):
        class Foo:
            bar = 'bar'

            def baz(self):
                pass

        vd.is_attribute_of('bar', Foo)
        vd.is_attribute_of('baz', Foo)

        expected = f'bagel is not an attribute of {Foo}'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_attribute_of('bagel', Foo)

    def test_is_directory(self):
        dirpath = '/foo/bar'
        expected = f'{dirpath} is not a directory or does not exist.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_directory(dirpath)

        with TemporaryDirectory() as root:
            vd.is_directory(root)

            filepath = Path(root, 'foo.txt')
            with open(filepath, 'w') as f:
                f.write('')

            expected = f'{filepath} is not a directory or does not exist.'
            with self.assertRaisesRegexp(ValidationError, expected):
                vd.is_directory(filepath)

    def test_is_file(self):
        filepath = '/foo/bar.txt'
        expected = f'{filepath} is not a file or does not exist.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_file(filepath)

        with TemporaryDirectory() as root:
            expected = f'{root} is not a file or does not exist.'
            with self.assertRaisesRegexp(ValidationError, expected):
                vd.is_file(root)

            filepath = Path(root, 'foo.txt')
            with open(filepath, 'w') as f:
                f.write('')
            vd.is_file(filepath)

    def test_is_not_missing_values(self):
        vd.is_not_missing_values([1, 0, 2, 3, 4])
        expected = r'Missing values: \[2, 3\]\.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_not_missing_values([0, 1, 4])

    def test_has_uniform_coordinate_count(self):
        coords = product(range(0, 3), range(8, 11))
        coords = list(map(list, coords))
        vd.has_uniform_coordinate_count(coords)
        coords *= 3
        vd.has_uniform_coordinate_count(coords)

        del coords[-1]
        expected = r'Non-uniform coordinate count. Missing coordinates: \[\[2, 10\]\]'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.has_uniform_coordinate_count(coords)

    def test_has_dense_coordinates(self):
        coords = product(range(0, 3), range(1, 4))
        coords = list(map(list, coords))
        vd.has_dense_coordinates(coords)

        coords = product(range(0, 3), range(0, 3))
        coords = list(map(list, coords))
        vd.has_dense_coordinates(coords)

        del coords[-3]
        expected = r'Non-dense coordinates. Missing coordinates: .*\[2, 0\]'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.has_dense_coordinates(coords)

    def test_coordinates_begin_at(self):
        coords = product(range(0, 3), range(0, 3))
        coords = list(map(list, coords))
        vd.coordinates_begin_at(coords, [0, 0])

        coords = product(range(1, 4), range(2, 4))
        coords = list(map(list, coords))
        vd.coordinates_begin_at(coords, [1, 2])

        coords = product(range(1, 4), range(0, 3))
        coords = list(map(list, coords))
        expected = r'Coordinates do not begin at \[0, 0\]\.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.coordinates_begin_at(coords, [0, 0])

        coords = product(range(1, 4), range(0, 3))
        coords = list(map(list, coords))
        expected = r'Coordinates do not begin at \[1, 1\]\.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.coordinates_begin_at(coords, [1, 1])

    def test_is_bucket_name(self):
        vd.is_bucket_name('foo')
        vd.is_bucket_name('foo123')
        vd.is_bucket_name('foo.123')
        vd.is_bucket_name('foo-bar.123')

        expected = [
            '{} is not a valid bucket name. Bucket names must:',
            '    - be between 3 and 63 characters',
            '    - only consist of lowercase letters, numbers, periods and hyphens',
            '    - begin and end with a letter or number'
        ]
        expected = '\n'.join(expected)

        # less than 3
        items = ['f', 'f' * 64, 'FooBar', '-foobar', 'foobar.']
        for item in items:
            # vd.is_bucket_name(item)
            with pytest.raises(ValidationError) as e:
                vd.is_bucket_name(item)
            self.assertEqual(str(e.value[0]), expected.format(item))

    def test_is_aws_region(self):
        vd.is_aws_region('us-west-2')
        vd.is_aws_region('ap-east-1')
        vd.is_aws_region('eu-north-1')

        expected = 'us-west-3 is not a valid AWS region.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_aws_region('us-west-3')

    def test_is_legal_directory(self):
        vd.is_legal_directory('/foo/bar')
        vd.is_legal_directory('/Foo/Bar')

        expected = '{} is not a legal directory path.'

        # starts with /
        dir_ = 'foo/bar'
        with self.assertRaisesRegexp(ValidationError, expected.format(dir_)):
            vd.is_legal_directory(dir_)

        # does not end with /
        dir_ = '/foo/bar/'
        with self.assertRaisesRegexp(ValidationError, expected.format(dir_)):
            vd.is_legal_directory(dir_)

        # bad chars
        dir_ = '/foo/bar.com'
        with self.assertRaisesRegexp(ValidationError, expected.format(dir_)):
            vd.is_legal_directory(dir_)

        dir_ = '/home/ubuntu/foo bar'
        with self.assertRaisesRegexp(ValidationError, expected.format(dir_)):
            vd.is_legal_directory(dir_)

    def test_is_metadata_type(self):
        vd.is_metadata_type('asset')
        vd.is_metadata_type('file')
        vd.is_metadata_type('asset-chunk')
        vd.is_metadata_type('file-chunk')

        expected = r"foobar is not a legal metadata type\."
        expected += r"\\nLegal metadata types: "
        expected += r"\[asset, file, asset-chunk, file-chunk\]"
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_metadata_type('foobar')

    def test_is_hidebound_directory(self):
        vd.is_hidebound_directory('/foo/bar/hidebound')

        expected = '/foo/bar directory is not named hidebound.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_hidebound_directory('/foo/bar')

        expected = '/foo/bar/Hidebound directory is not named hidebound.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_hidebound_directory('/foo/bar/Hidebound')

    def test_is_http_method(self):
        methods = ['get', 'put', 'post', 'delete', 'patch']
        for method in methods:
            vd.is_http_method(method)

        expected = 'trace is not a legal HTTP method.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_http_method('trace')

    def test_is_workflow(self):
        steps = ['delete', 'update', 'create', 'export']
        vd.is_workflow(steps)

        steps = ['delete', 'update', 'create', 'export', 'foo', 'bar']
        expected = 'bar.*foo.*are not legal workflow steps. '
        expected += r"Legal steps: \['delete', 'update', 'create', 'export'\]\."
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_workflow(steps)

    def test_is_one_of(self):
        class Foo(Model):
            foo = StringType(required=True)

        class Bar(Model):
            bar = StringType(required=True)

        vd.is_one_of(dict(bar='bar'), [])

        models = [Foo, Bar]
        vd.is_one_of(dict(bar='bar'), models)

        expected = 'taco.*Rogue field'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_one_of(dict(taco='taco'), models)

    def test_is_cluster_option_type(self):
        vd.is_cluster_option_type('string')
        vd.is_cluster_option_type('int')
        vd.is_cluster_option_type('float')
        vd.is_cluster_option_type('bool')
        vd.is_cluster_option_type('mapping')
        vd.is_cluster_option_type('select')

        expected = r'foobar is not a legal cluster option type\.'
        expected += r'\\nLegal cluster option types: '
        expected += r'\[bool, float, int, mapping, select, string\]'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_cluster_option_type('foobar')
