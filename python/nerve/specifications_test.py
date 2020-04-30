from collections import defaultdict
import unittest

from schematics.exceptions import DataError

import nerve.specifications as spec
# ------------------------------------------------------------------------------


class SpecificationsTests(unittest.TestCase):
    def test_raw001(self):
        item = dict(
            project='proj001',
            descriptor='desc',
            version=1,
            frame=1,
            extension='png',
            height=1024,
            width=1024,
        )
        data = defaultdict(lambda: [])
        for i in range(3):
            for k, v in item.items():
                data[k].append(v)

        spec.Raw001(data).validate()

        expected = '1023 != 1024'
        data['width'][-1] = 1023
        with self.assertRaisesRegexp(DataError, expected):
            spec.Raw001(data).validate()

        expected = '1000 != 1024'
        data['height'][-1] = 1000
        with self.assertRaisesRegexp(DataError, expected):
            spec.Raw001(data).validate()

        expected = '.*PNG.* is not a valid extension.'
        data['extension'][-1] = 'PNG'
        with self.assertRaisesRegexp(DataError, expected):
            spec.Raw001(data).validate()

        expected = 'jpeg != png'
        data['extension'][-1] = 'jpeg'
        with self.assertRaisesRegexp(DataError, expected):
            spec.Raw001(data).validate()
