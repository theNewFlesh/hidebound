import unittest

import nerve.validators as vd
from nerve.validators import ValidationError
# ------------------------------------------------------------------------------


class DatabaseTests(unittest.TestCase):
    def test_validator(self):
        message = '{} is not foo'
        @vd.validator(message)
        def func(item):
            return item == 'foo'

        func('foo')

        expected = message.format('bar')
        with self.assertRaisesRegexp(ValidationError, expected):
            func('bar')

        expected = message.format(1)
        with self.assertRaisesRegexp(ValidationError, expected):
            func(1)

    def test_is_project(self):
        vd.is_project('proj001')

        expected = '"proj-001" is not a valid project name.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_project('proj-001')

        expected = '"bigfancyproj001" is not a valid project name.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_project('bigfancyproj001')

        expected = '"proj00001" is not a valid project name.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_project('proj00001')

    def test_is_descriptor(self):
        vd.is_descriptor('desc')

        expected = '"master-desc" is not a valid descriptor.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_descriptor('master-desc')

        expected = '"Desc" is not a valid descriptor.'
        with self.assertRaisesRegexp(ValidationError, expected):
            vd.is_descriptor('Desc')

        expected = '"" is not a valid descriptor.'
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

        expected = r'"\$\$\$" is not a valid extension\.'
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
