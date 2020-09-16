from itertools import product
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np
from schematics.exceptions import ValidationError

import hidebound.core.validators as vd
# ------------------------------------------------------------------------------


class DatabaseTests(unittest.TestCase):
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

        expected = r'\[0, 0, 1000\] is not a valid coordinate\.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_coordinate([0, 0, 1000])

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
        vd.is_not_missing_values([0, 1, 2, 3, 4])
        expected = r'Missing frames: \[2, 3\]\.'
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
