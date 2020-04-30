from pathlib import Path
import os
import re
from tempfile import TemporaryDirectory
import unittest

import numpy as np
from pandas import DataFrame

from nerve.database import Database
from nerve.specification_base import SpecificationBase
from nerve.specification_base import FileSpecificationBase
from nerve.specification_base import SequenceSpecificationBase
from nerve.specification_base import ComplexSpecificationBase
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
        'error',
        'asset_name',
        'asset_path',
        'asset_type',
        # 'asset_id',
    ]

    def get_data(self, root, nans=False):
        data = [
            [0, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v001', 'p-proj001_s-spec001_d-pizza_v001_c000-001_f0001.png',  None                                ],  # noqa E501 E241
            [0, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v001', 'p-proj001_s-spec001_d-pizza_v001_c000-001_f0002.png',  None                                ],  # noqa E501 E241
            [0, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v001', 'p-proj001_s-spec001_d-pizza_v001_c000-001_f0003.png',  None                                ],  # noqa E501 E241
            [1, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-000_f0001.png',  None                                ],  # noqa E501 E241
            [1, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-000_f0002.png',  None                                ],  # noqa E501 E241
            [1, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-000_f0003.png',  None                                ],  # noqa E501 E241
            [1, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-000_f0004.png',  None                                ],  # noqa E501 E241
            [2, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-001_f0001.png',  None                                ],  # noqa E501 E241
            [2, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-001_f0002.png',  None                                ],  # noqa E501 E241
            [2, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-001_f0003.png',  None                                ],  # noqa E501 E241
            [2, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c000-001_f0004.png',  None                                ],  # noqa E501 E241
            [3, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-kiwi_v003_c000-001_f0001.png', ' Inconsistent descriptor field token'],  # noqa E501 E241
            [3, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-pizza_v003_c000-001_f0002.png',  None                                ],  # noqa E501 E241
            [3, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-PIZZA_v003_c000-001_f0003.png',  'Illegal descriptor field token'    ],  # noqa E501 E241
            [3, 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-pizza_v003_c000-001_f0004.png',  None                                ],  # noqa E501 E241
            [3, None,      'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec0001_d-pizza_v003_c000-001_f0005.png', 'Illegal specification field token' ],  # noqa E501 E241
            [3, None,      'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'misc.txt',                                             'SpecificationBase not found'       ],  # noqa E501 E241
            [4, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v001',   'p-proj001_s-spec002_d-taco_v001_f0000.exr',            None                                ],  # noqa E501 E241
            [4, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v001',   'p-proj001_s-spec002_d-taco_v001_f0001.exr',            None                                ],  # noqa E501 E241
            [4, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v001',   'p-proj001_s-spec002_d-taco_v001_f0002.exr',            None                                ],  # noqa E501 E241
            [5, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v001_f0000.exr',            'Invalid asset directory name'      ],  # noqa E501 E241
            [5, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v002_f0001.exr',            None                                ],  # noqa E501 E241
            [5, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v002',                      'Expected "_"'                      ],  # noqa E501 E241
            [5, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v02_f0003.exr',             'Illegal version field token'       ],  # noqa E501 E241
            [6, 'vdb001',  'proj002/vdb001',                                         'p-proj002_s-vdb001_d-bagel_v001.vdb',                  'Specification not found'           ],  # noqa E501 E241
            [6, 'vdb001',  'proj002/vdb001',                                         'p-proj002_s-vdb001_d-bagel_v002.vdb',                  'Specification not found'           ],  # noqa E501 E241
            [6, 'vdb001',  'proj002/vdb001',                                         'p-proj002_s-vdb001_d-bagel_v003.vdb',                  'Specification not found'           ],  # noqa E501 E241
        ]

        data = DataFrame(data)
        data.columns = ['asset_id', 'specification', 'asset_path', 'filename', 'error']

        data.asset_path = data.asset_path.apply(lambda x: root + '/' + x)
        data['asset_name'] = data.asset_path.apply(lambda x: x.split('/')[-1])

        data['fullpath'] = data\
            .apply(lambda x: Path(root, x.asset_path, x.filename), axis=1)

        Spec001, Spec002, BadSpec = self.get_specifications()
        specs = {
            Spec001.name: Spec001,
            Spec002.name: Spec002,
            None: np.nan,
            'vdb001': np.nan,
        }
        data['specification_class'] = data.specification\
            .apply(lambda x: specs[x])

        if nans:
            data = data.applymap(lambda x: np.nan if x is None else x)
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
        data['fullpath'] = files.asset_path
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

    def test_update_error(self):
        Spec001, Spec002, BadSpec = self.get_specifications()

        with TemporaryDirectory() as root:
            files = self.create_files(root)
            data = Database(root, [Spec001, Spec002]).update().data

            keys = files.fullpath.tolist()
            lut = dict(zip(keys, files.error.tolist()))

            data = data[data.fullpath.apply(lambda x: x in keys)]

            regexes = data.fullpath.apply(lambda x: lut[x.as_posix()]).tolist()
            results = data.error.apply(lambda x: x[0]).tolist()
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
        data = self.get_data('/tmp')

        error = 'Invalid asset directory name'
        mask = data.error == error
        data.loc[mask, 'error'] = np.nan

        cols = ['specification_class', 'fullpath', 'error']
        data = data[cols]

        Database._validate_filepath(data)
        result = data.loc[mask, 'error'].tolist()[0]
        self.assertRegex(result, error)

    def test_add_filename_data(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        data = [
            [
                Spec001,
                'p-proj001_s-spec001_d-desc_v001_c000-000_f0001.png',
                np.nan,
                'proj001', 'spec001', 'desc', 1, [0, 0], 1, 'png'
            ],
            [
                Spec001,
                'p-proj001_s-spec001_d-desc_v001_c000-000_f0002.png',
                np.nan,
                'proj001', 'spec001', 'desc', 1, [0, 0], 2, 'png'
            ],
            [
                Spec002,
                'p-proj002_s-spec002_d-MASTER_v001_f0001.png',
                'Error',
                np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan
            ],
            [
                Spec002,
                'p-proj002_s-spec002_d-desc_v001_f0002.png',
                np.nan,
                'proj002', 'spec002', 'desc', 1, np.nan, 2, 'png'
            ],
            [
                np.nan,
                'misc.txt',
                'Error',
                np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan
            ],
        ]
        data = DataFrame(data)
        cols = [
            'project', 'specification', 'descriptor', 'version', 'coordinate',
            'frame', 'extension'
        ]
        data.columns = ['specification_class', 'filename', 'error'] + cols
        temp = data.copy()

        Database._add_filename_data(data)
        for col in cols:
            result = data[col].fillna('null').tolist()
            expected = temp[col].fillna('null').tolist()
            self.assertEqual(result, expected)

    def test_add_asset_id(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        data = [
            [
                Spec001,
                '/tmp/p-proj001_s-spec001_d-desc_v001/p-proj001_s-spec001_d-desc_v001_c000-000_f0001.png',  # noqa E501
                np.nan,
            ],
            [
                Spec001,
                '/tmp/p-proj001_s-spec001_d-desc_v001/p-proj001_s-spec001_d-desc_v001_c000-000_f0002.png',  # noqa E501
                np.nan,
            ],
            [
                Spec002,
                '/tmp/p-proj002_s-spec002_d-MASTER_v001/p-proj002_s-spec002_d-MASTER_v001_f0001.png',  # noqa E501
                'Error',
            ],
            [
                Spec002,
                '/tmp/p-proj002_s-spec002_d-desc_v001/p-proj002_s-spec002_d-desc_v001_f0002.png',
                np.nan,
            ],
            [
                np.nan,
                '/tmp/proj002/misc.txt',
                'Error',
            ],
        ]

        data = DataFrame(data)
        data.columns = ['specification_class', 'fullpath', 'error']

        Database._add_asset_id(data)
        result = data['asset_id'].dropna().nunique()
        self.assertEqual(result, 2)

    def test_add_asset_name(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        data = [
            [
                Spec001,
                '/tmp/p-proj001_s-spec001_d-desc_v001/p-proj001_s-spec001_d-desc_v001_c000-000_f0001.png',  # noqa E501
                np.nan,
            ],
            [
                Spec001,
                '/tmp/p-proj001_s-spec001_d-desc_v001/p-proj001_s-spec001_d-desc_v001_c000-000_f0002.png',  # noqa E501
                np.nan,
            ],
            [
                Spec002,
                '/tmp/p-proj002_s-spec002_d-MASTER_v001/p-proj002_s-spec002_d-MASTER_v001_f0001.png',  # noqa E501
                'Error',
            ],
            [
                Spec002,
                '/tmp/p-proj002_s-spec002_d-desc_v001/p-proj002_s-spec002_d-desc_v001_f0002.png',
                np.nan,
            ],
            [
                np.nan,
                '/tmp/proj002/misc.txt',
                'Error',
            ],
        ]

        data = DataFrame(data)
        data.columns = ['specification_class', 'fullpath', 'error']

        Database._add_asset_name(data)
        result = data['asset_name'].dropna().nunique()
        self.assertEqual(result, 2)

    def test_add_asset_path(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        data = [
            [
                Spec001,
                '/tmp/p-proj001_s-spec001_d-desc_v001/p-proj001_s-spec001_d-desc_v001_c000-000_f0001.png',  # noqa E501
                np.nan,
            ],
            [
                Spec001,
                '/tmp/p-proj001_s-spec001_d-desc_v001/p-proj001_s-spec001_d-desc_v001_c000-000_f0002.png',  # noqa E501
                np.nan,
            ],
            [
                Spec002,
                '/tmp/p-proj002_s-spec002_d-MASTER_v001/p-proj002_s-spec002_d-MASTER_v001_f0001.png',  # noqa E501
                'Error',
            ],
            [
                Spec002,
                '/tmp/p-proj002_s-spec002_d-desc_v001/p-proj002_s-spec002_d-desc_v001_f0002.png',
                np.nan,
            ],
            [
                np.nan,
                '/tmp/proj002/misc.txt',
                'Error',
            ],
        ]

        data = DataFrame(data)
        data.columns = ['specification_class', 'fullpath', 'error']
        expected = data.fullpath\
            .apply(lambda x: Path(x).parent).apply(str).tolist()
        expected[-1] = 'nan'

        Database._add_asset_path(data)
        result = data['asset_path'].apply(str).tolist()
        self.assertEqual(result, expected)

        result = data['asset_path'].dropna().nunique()
        self.assertEqual(result, 3)

    def test_add_asset_type(self):
        class Spec001(FileSpecificationBase):
            name = 'spec001'
            filename_fields = ['specification']

        class Spec002(SequenceSpecificationBase):
            name = 'spec002'
            filename_fields = ['specification']

        class Spec003(ComplexSpecificationBase):
            name = 'spec003'
            filename_fields = ['specification']

        data = DataFrame()
        data['specification_class'] = [
            Spec001,
            Spec002,
            Spec003,
            np.nan,
        ]
        Database._add_asset_type(data)
        result = data['asset_type'].fillna('null').tolist()
        expected = ['file', 'sequence', 'complex', 'null']
        self.assertEqual(result, expected)

    def test_cleanup(self):
        data = DataFrame()
        result = Database._cleanup(data).columns.tolist()
        self.assertEqual(result, self.columns)

        data['fullpath'] = [np.nan, Path('/foo/bar'), Path('/bar/foo')]
        data['version'] = [1, 2, 3]
        expected = [np.nan, '/foo/bar', '/bar/foo']
        result = Database._cleanup(data).fullpath.tolist()
        self.assertEqual(result, expected)

        result = Database._cleanup(data).columns.tolist()
        self.assertEqual(result, self.columns)
