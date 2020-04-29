from pathlib import Path
import os
from tempfile import TemporaryDirectory
import unittest

from pandas import DataFrame

from nerve.database import Database
from nerve.specification_base import SpecificationBase
# ------------------------------------------------------------------------------


class DatabaseTests(unittest.TestCase):
    columns = [
        'project',
        'specification',
        'descriptor',
        'version',
        'coordinate',
        'frame',
        'extension',
        'filename',
        'fullpath',
        'errors',
        'asset_name',
        'asset_id',
    ]

    def get_data(self, root):
        data = [
            [0, 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v001', 'p-proj001_s-spec001_d-pizza_v001_c000-001_f0001.png', None                                ],  # noqa E501 E241
            [0, 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v001', 'p-proj001_s-spec001_d-pizza_v001_c000-001_f0002.png', None                                ],  # noqa E501 E241
            [0, 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v001', 'p-proj001_s-spec001_d-pizza_v001_c000-001_f0003.png', None                                ],  # noqa E501 E241
            [1, 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-000_f0001.png', None                                ],  # noqa E501 E241
            [1, 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-000_f0002.png', None                                ],  # noqa E501 E241
            [1, 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-000_f0003.png', None                                ],  # noqa E501 E241
            [1, 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-000_f0004.png', None                                ],  # noqa E501 E241
            [2, 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-001_f0001.png', None                                ],  # noqa E501 E241
            [2, 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-001_f0002.png', None                                ],  # noqa E501 E241
            [2, 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-001_f0003.png', None                                ],  # noqa E501 E241
            [2, 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-001_f0004.png', None                                ],  # noqa E501 E241
            [3, 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-kiwi_v003_c000-001_f0001.png', 'Inconsistent descriptor field token'],  # noqa E501 E241
            [3, 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-pizza_v003_c000-001_f0002.png', None                                ],  # noqa E501 E241
            [3, 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-PIZZA_v003_c000-001_f0003.png', 'Illegal descriptor field token'    ],  # noqa E501 E241
            [3, 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-pizza_v003_c000-001_f0004.png', None                                ],  # noqa E501 E241
            [3, 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'misc.txt',                                            'SpecificationBase not found'       ],  # noqa E501 E241
            [4, 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v001',   'p-proj001_s-spec002_d-taco_v001_f0000.exr',           None                                ],  # noqa E501 E241
            [4, 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v001',   'p-proj001_s-spec002_d-taco_v001_f0001.exr',           None                                ],  # noqa E501 E241
            [4, 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v001',   'p-proj001_s-spec002_d-taco_v001_f0002.exr',           None                                ],  # noqa E501 E241
            [5, 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v001_f0000.exr',          'Invalid asset directory name'       ],  # noqa E501 E241
            [5, 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v002_f0001.exr',           None                                ],  # noqa E501 E241
            [5, 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v002',                    'Expected "_"'                       ],  # noqa E501 E241
            [5, 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v02_f0003.exr',           'Illegal version field token'        ],  # noqa E501 E241
            [6, 'proj002/vdb001',                                         'p-proj002_s-vdb001_d-bagel_v001.vdb',                'Specification not found'            ],  # noqa E501 E241
            [6, 'proj002/vdb001',                                         'p-proj002_s-vdb001_d-bagel_v002.vdb',                'Specification not found'            ],  # noqa E501 E241
            [6, 'proj002/vdb001',                                         'p-proj002_s-vdb001_d-bagel_v003.vdb',                'Specification not found'            ],  # noqa E501 E241
        ]

        data = DataFrame(data)
        data.columns = ['asset_id', 'asset_dir', 'filename', 'error']
        data['fullpath'] = data\
            .apply(lambda x: Path(root, x.asset_dir, x.filename), axis=1)
        return data

    def create_files(self, root):
        data = self.get_data(root)
        for fullpath in data.fullpath.tolist():
            os.makedirs(fullpath.parent, exist_ok=True)
            with open(fullpath, 'w') as f:
                f.write('')
        return data

    def get_specifications(self):
        class Spec001(SpecificationBase):
            name = 'spec001'
            filename_fields = [
                'project',
                'specification',
                'descriptor',
                'version',
                'coordinate',
                'frame',
                'extension',
            ]

            def get_asset_path(self, filepath):
                return Path(filepath).parents[0]

        class Spec002(SpecificationBase):
            name = 'spec002'
            filename_fields = [
                'project',
                'specification',
                'descriptor',
                'version',
                'frame',
                'extension',
            ]

            def get_asset_path(self, filepath):
                return Path(filepath).parents[0]

        class BadSpec:
            pass

        return Spec001, Spec002, BadSpec

    def test_init(self):
        Spec001, Spec002, BadSpec = self.get_specifications()

        expected = '/foo is not a directory or does not exist.'
        with self.assertRaisesRegexp(FileNotFoundError, expected):
            Database('/foo', [Spec001])

        with TemporaryDirectory() as root:
            self.create_files(root)
            expected = 'SpecificationBase may only contain subclasses of'
            expected += ' SpecificationBase. Found: .*.'

            with self.assertRaisesRegexp(TypeError, expected):
                Database(root, [BadSpec])

            with self.assertRaisesRegexp(TypeError, expected):
                Database(root, [Spec001, BadSpec])

        with TemporaryDirectory() as root:
            self.create_files(root)
            Database(root)
            Database(root, [Spec001])
            Database(root, [Spec001, Spec002])

    def test_update_no_files(self):
        Spec001, Spec002, BadSpec = self.get_specifications()

        with TemporaryDirectory() as root:
            result = Database(root, [Spec001]).update().data
            self.assertEqual(len(result), 0)
            self.assertEqual(result.columns.tolist(), self.columns)

    def test_update_errors(self):
        Spec001, Spec002, BadSpec = self.get_specifications()

        with TemporaryDirectory() as root:
            files = self.create_files(root)
            data = Database(root, [Spec001, Spec002]).update().data

            keys = files.fullpath.tolist()
            lut = dict(zip(keys, files.error.tolist()))

            data = data[data.fullpath.apply(lambda x: x in keys)]

            regexes = data.fullpath.apply(lambda x: lut[x.as_posix()]).tolist()
            results = data.errors.apply(lambda x: x[0]).tolist()
            for result, regex in zip(results, regexes):
                self.assertRegex(result, regex)
