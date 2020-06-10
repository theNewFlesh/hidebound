from collections import defaultdict
import unittest

from schematics.exceptions import DataError

import hidebound.core.specifications as spec
# ------------------------------------------------------------------------------


class SpecificationsTests(unittest.TestCase):
    def test_raw001(self):
        item = dict(
            project='proj001',
            descriptor='desc',
            version=1,
            frame=1,
            extension='jpg',
            height=5,
            width=4,
            channels=1,
        )
        data = defaultdict(lambda: [])
        for i in range(3):
            for k, v in item.items():
                data[k].append(v)

        spec.Raw001(data).validate()

        expected = '.*JPG.* is not a valid extension.'
        data['extension'][-1] = 'JPG'
        with self.assertRaisesRegexp(DataError, expected):
            spec.Raw001(data).validate()

        expected = 'png != jpg'
        data['extension'][-1] = 'png'
        with self.assertRaisesRegexp(DataError, expected):
            spec.Raw001(data).validate()

        expected = r'2 is not in \[1, 3\]'
        data['extension'][-1] = 'jpg'
        data['channels'][-1] = 2
        with self.assertRaisesRegexp(DataError, expected):
            spec.Raw002(data).validate()

    def test_raw002(self):
        item = dict(
            project='proj001',
            descriptor='desc',
            version=1,
            coordinate=[0, 1],
            frame=1,
            extension='jpg',
            height=5,
            width=4,
            channels=1,
        )
        data = defaultdict(lambda: [])
        for i in range(3):
            for k, v in item.items():
                data[k].append(v)

        spec.Raw002(data).validate()

        expected = '.*JPG.* is not a valid extension.'
        data['extension'][-1] = 'JPG'
        with self.assertRaisesRegexp(DataError, expected):
            spec.Raw002(data).validate()

        expected = 'png != jpg'
        data['extension'][-1] = 'png'
        with self.assertRaisesRegexp(DataError, expected):
            spec.Raw002(data).validate()

        expected = r'2 is not in \[1, 3\]'
        data['extension'][-1] = 'jpg'
        data['channels'][-1] = 2
        with self.assertRaisesRegexp(DataError, expected):
            spec.Raw002(data).validate()
