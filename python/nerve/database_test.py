from pathlib import Path
import os
import re
from tempfile import TemporaryDirectory
import unittest

import numpy as np
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
        'asset_path',
        'asset_type',
        # 'asset_id',
    ]

    def get_data(self, root):
        data = [
            [0, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v001', 'p-proj001_s-spec001_d-pizza_v001_c000-001_f0001.png', None                                ],  # noqa E501 E241
            [0, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v001', 'p-proj001_s-spec001_d-pizza_v001_c000-001_f0002.png', None                                ],  # noqa E501 E241
            [0, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v001', 'p-proj001_s-spec001_d-pizza_v001_c000-001_f0003.png', None                                ],  # noqa E501 E241
            [1, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-000_f0001.png', None                                ],  # noqa E501 E241
            [1, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-000_f0002.png', None                                ],  # noqa E501 E241
            [1, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-000_f0003.png', None                                ],  # noqa E501 E241
            [1, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-000_f0004.png', None                                ],  # noqa E501 E241
            [2, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-001_f0001.png', None                                ],  # noqa E501 E241
            [2, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-001_f0002.png', None                                ],  # noqa E501 E241
            [2, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-001_f0003.png', None                                ],  # noqa E501 E241
            [2, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-001_f0004.png', None                                ],  # noqa E501 E241
            [3, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-kiwi_v003_c000-001_f0001.png', 'Inconsistent descriptor field token'],  # noqa E501 E241
            [3, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-pizza_v003_c000-001_f0002.png', None                                ],  # noqa E501 E241
            [3, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-PIZZA_v003_c000-001_f0003.png', 'Illegal descriptor field token'    ],  # noqa E501 E241
            [3, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-pizza_v003_c000-001_f0004.png', None                                ],  # noqa E501 E241
            [3, None,      'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec0001_d-pizza_v003_c000-001_f0005.png','Illegal specification field token' ],  # noqa E501 E241
            [3, None,      'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'misc.txt',                                            'SpecificationBase not found'       ],  # noqa E501 E241
            [4, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v001',   'p-proj001_s-spec002_d-taco_v001_f0000.exr',           None                                ],  # noqa E501 E241
            [4, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v001',   'p-proj001_s-spec002_d-taco_v001_f0001.exr',           None                                ],  # noqa E501 E241
            [4, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v001',   'p-proj001_s-spec002_d-taco_v001_f0002.exr',           None                                ],  # noqa E501 E241
            [5, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v001_f0000.exr',          'Invalid asset directory name'       ],  # noqa E501 E241
            [5, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v002_f0001.exr',           None                                ],  # noqa E501 E241
            [5, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v002',                    'Expected "_"'                       ],  # noqa E501 E241
            [5, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v02_f0003.exr',           'Illegal version field token'        ],  # noqa E501 E241
            [6, 'vdb001',  'proj002/vdb001',                                         'p-proj002_s-vdb001_d-bagel_v001.vdb',                'Specification not found'            ],  # noqa E501 E241
            [6, 'vdb001',  'proj002/vdb001',                                         'p-proj002_s-vdb001_d-bagel_v002.vdb',                'Specification not found'            ],  # noqa E501 E241
            [6, 'vdb001',  'proj002/vdb001',                                         'p-proj002_s-vdb001_d-bagel_v003.vdb',                'Specification not found'            ],  # noqa E501 E241
        ]

        data = DataFrame(data)
        data.columns = ['asset_id', 'spec', 'asset_dir', 'filename', 'error']
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

    def get_directory_to_dataframe_data(self, root):
        files = self.get_data(root)
        data = DataFrame()
        data['filename'] = files.filename
        data['fullpath'] = files.asset_dir
        data.fullpath = data\
            .apply(lambda x: Path(x.fullpath, x.filename), axis=1)
        data['extension'] = files\
            .filename.apply(lambda x: os.path.splitext(x)[1:])
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

    def test_update_exclude(self):
        with TemporaryDirectory() as root:
            expected = self.create_files(root).fullpath\
                .apply(lambda x: x.as_posix()).tolist()
            regex = r'misc\.txt|vdb'
            expected = list(filter(lambda x: not re.search(regex, x), expected))
            expected = sorted(expected)

            result = Database(root, exclude_regex=regex)\
                .update().data.fullpath.tolist()
            result = sorted(result)
            self.assertEqual(result, expected)

    def test_update_include(self):
        with TemporaryDirectory() as root:
            expected = self.create_files(root).fullpath\
                .apply(lambda x: x.as_posix()).tolist()
            regex = r'misc\.txt|vdb'
            expected = list(filter(lambda x: re.search(regex, x), expected))
            expected = sorted(expected)

            result = Database(root, include_regex=regex)\
                .update().data.fullpath.tolist()
            result = sorted(result)
            self.assertEqual(result, expected)

    def test_update_include_exclude(self):
        with TemporaryDirectory() as root:
            expected = self.create_files(root).fullpath\
                .apply(lambda x: x.as_posix()).tolist()
            i_regex = r'pizza'
            expected = list(filter(lambda x: re.search(i_regex, x), expected))
            e_regex = r'misc\.txt|vdb'
            expected = list(filter(lambda x: not re.search(e_regex, x), expected))
            expected = sorted(expected)

            result = Database(root, include_regex=i_regex, exclude_regex=e_regex)\
                .update().data.fullpath.tolist()
            result = sorted(result)
            self.assertEqual(result, expected)

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

    def test_add_specification(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        specs = {Spec001.name: Spec001, Spec002.name: Spec002}

        data = self.get_directory_to_dataframe_data('/tmp')
        Database._add_specification(data, specs)

        result = data.specification.tolist()
        expected = data.specification
        self.assertEqual(result, expected.tolist())

    def test_validate_filepath(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        data = [
            [
                Spec001,
                '/tmp/p-proj001_s-spec001_d-desc_v001/p-proj001_s-spec001_d-desc_v001_f0001.png',
                set([]),
            ],
            [
                Spec001,
                '/tmp/p-proj001_s-spec001_d-desc_v001/p-proj001_s-spec001_d-desc_v001_f0002.png',
                set([]),
            ],
            [
                Spec002,
                '/tmp/p-proj001_s-spec001_d-desc_v001/p-proj001_s-spec001_d-MASTER_v001_f0001.png',
                set(['Error']),
            ],
            [
                Spec002,
                '/tmp/p-proj001_s-spec001_d-bananana_v001/p-proj001_s-spec001_d-desc_v001_f0002.png',  # noqa E501
                set([]),
            ],
            [
                np.nan,
                '/tmp/p-proj002_s-spec001_d-desc_v001/misc.txt',
                set(['Error']),
            ],
        ]
        data = DataFrame(data)
        data.columns = ['specification_class', 'fullpath', 'errors']

        Database._validate_filepath(data)
        result = str(data.errors.apply(list).tolist()[3][0])
        self.assertRegex(result, 'Invalid asset directory name')

    def test_add_filename_data(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        data = [
            [
                Spec001,
                'p-proj001_s-spec001_d-desc_v001_c000-000_f0001.png',
                set([]),
                'proj001', 'spec001', 'desc', 1, [0, 0], 1, 'png'
            ],
            [
                Spec001,
                'p-proj001_s-spec001_d-desc_v001_c000-000_f0002.png',
                set([]),
                'proj001', 'spec001', 'desc', 1, [0, 0], 2, 'png'
            ],
            [
                Spec002,
                'p-proj002_s-spec002_d-MASTER_v001_f0001.png',
                set(['Error']),
                np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan
            ],
            [
                Spec002,
                'p-proj002_s-spec002_d-desc_v001_f0002.png',
                set([]),
                'proj002', 'spec002', 'desc', 1, np.nan, 2, 'png'
            ],
            [
                np.nan,
                'misc.txt',
                set(['Error']),
                np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan
            ],
        ]
        data = DataFrame(data)
        cols = [
            'project', 'specification', 'descriptor', 'version', 'coordinate',
            'frame', 'extension'
        ]
        data.columns = ['specification_class', 'filename', 'errors'] + cols
        temp = data.copy()

        Database._add_filename_data(data)
        for col in cols:
            result = data[col].fillna('null').tolist()
            expected = temp[col].fillna('null').tolist()
            self.assertEqual(result, expected)

    # def test_add_asset_id(self):
    #     pass

    # def test_add_asset_name(self):
    #     pass

    # def test_add_asset_path(self):
    #     pass

    # def test_add_asset_type(self):
    #     pass

    # def test_cleanup(self):
    #     pass
