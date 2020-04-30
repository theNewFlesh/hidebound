from copy import copy
import unittest

from schematics.exceptions import DataError

import nerve.specifications as spec
# ------------------------------------------------------------------------------


class SpecificationsTests(unittest.TestCase):
    def test_raw001(self):
        data = dict(
            project='proj001',
            descriptor='desc',
            version=1,
            frame=1,
            extension='png',
            height=1024,
            width=1024,
        )
        spec.Raw001(data).validate()

        expected = '1023 != 1024'
        x = copy(data)
        x['width'] = 1023
        with self.assertRaisesRegexp(DataError, expected):
            spec.Raw001(x).validate()

        expected = '1000 != 1024'
        x = copy(data)
        x['height'] = 1000
        with self.assertRaisesRegexp(DataError, expected):
            spec.Raw001(x).validate()

        expected = '.*PNG.* is not a valid extension.'
        x = copy(data)
        x['extension'] = 'PNG'
        with self.assertRaisesRegexp(DataError, expected):
            spec.Raw001(x).validate()

        expected = 'jpeg != png'
        x['extension'] = 'jpeg'
        with self.assertRaisesRegexp(DataError, expected):
            spec.Raw001(x).validate()
