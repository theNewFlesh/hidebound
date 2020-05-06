from pathlib import Path
from tempfile import TemporaryDirectory
import os
import re
import unittest

from pandas import DataFrame
from schematics.types import ListType, IntType, StringType
import numpy as np
import skimage.io

from hidebound.database import Database
from hidebound.specification_base import ComplexSpecificationBase
from hidebound.specification_base import FileSpecificationBase
from hidebound.specification_base import SequenceSpecificationBase
from hidebound.specification_base import SpecificationBase
import hidebound.traits as tr
import hidebound.validators as vd
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
        'filepath',
        'file_error',
        'file_traits',
        'asset_name',
        'asset_path',
        'asset_type',
        'asset_traits',
        'asset_error',
        'asset_valid',
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
            [4, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v001',   'p-proj001_s-spec002_d-taco_v001_f0000.jpg',            None                                ],  # noqa E501 E241
            [4, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v001',   'p-proj001_s-spec002_d-taco_v001_f0001.jpg',            None                                ],  # noqa E501 E241
            [4, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v001',   'p-proj001_s-spec002_d-taco_v001_f0002.jpg',            None                                ],  # noqa E501 E241
            [5, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v001_f0000.jpg',            'Invalid asset directory name'      ],  # noqa E501 E241
            [5, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v002_f0001.jpg',            None                                ],  # noqa E501 E241
            [5, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v002',                      'Expected "_"'                      ],  # noqa E501 E241
            [5, 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v02_f0003.jpg',             'Illegal version field token'       ],  # noqa E501 E241
            [6, 'vdb001',  'proj002/vdb001',                                         'p-proj002_s-vdb001_d-bagel_v001.vdb',                  'Specification not found'           ],  # noqa E501 E241
            [6, 'vdb001',  'proj002/vdb001',                                         'p-proj002_s-vdb001_d-bagel_v002.vdb',                  'Specification not found'           ],  # noqa E501 E241
            [6, 'vdb001',  'proj002/vdb001',                                         'p-proj002_s-vdb001_d-bagel_v003.vdb',                  'Specification not found'           ],  # noqa E501 E241
        ]

        data = DataFrame(data)
        data.columns = ['asset_id', 'specification', 'asset_path', 'filename', 'file_error']

        data.asset_path = data.asset_path.apply(lambda x: root + '/' + x)
        data['asset_name'] = data.asset_path.apply(lambda x: x.split('/')[-1])

        data['filepath'] = data\
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
        for filepath in data.filepath.tolist():
            os.makedirs(filepath.parent, exist_ok=True)

            ext = os.path.splitext(filepath)[-1][1:]
            if ext in ['png', 'jpg']:
                img = np.zeros((5, 4, 3), dtype=np.uint8)
                skimage.io.imsave(filepath.as_posix(), img)
            else:
                with open(filepath, 'w') as f:
                    f.write('')
        return data

    def get_directory_to_dataframe_data(self, root):
        files = self.get_data(root)
        data = DataFrame()
        data['filename'] = files.filename
        data['filepath'] = files.asset_path
        data.filepath = data\
            .apply(lambda x: Path(x.filepath, x.filename), axis=1)
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
            coordinate = ListType(ListType(IntType()), required=True)
            frame = ListType(IntType(), required=True)
            extension = ListType(
                StringType(),
                required=True,
                validators=[lambda x: vd.is_eq(x, 'png')]
            )

            height = ListType(
                IntType(),
                required=True, validators=[lambda x: vd.is_eq(x, 5)]
            )
            width = ListType(
                IntType(),
                required=True, validators=[lambda x: vd.is_eq(x, 4)]
            )
            channels = ListType(
                IntType(),
                required=True, validators=[lambda x: vd.is_eq(x, 3)]
            )

            file_traits = dict(
                width=tr.get_image_width,
                height=tr.get_image_height,
                channels=tr.get_image_channels,
            )

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

            frame = ListType(IntType(), required=True)
            extension = ListType(
                StringType(),
                required=True,
                validators=[lambda x: vd.is_eq(x, 'jpg')]
            )

            height = ListType(
                IntType(),
                required=True, validators=[lambda x: vd.is_eq(x, 5)]
            )
            width = ListType(
                IntType(),
                required=True, validators=[lambda x: vd.is_eq(x, 4)]
            )
            channels = ListType(
                IntType(),
                required=True, validators=[lambda x: vd.is_eq(x, 3)]
            )

            file_traits = dict(
                width=tr.get_image_width,
                height=tr.get_image_height,
                channels=tr.get_image_channels,
            )

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

    # UPDATE--------------------------------------------------------------------
    def test_update(self):
        with TemporaryDirectory() as root:
            Spec001, Spec002, BadSpec = self.get_specifications()

            expected = self.create_files(root).filepath\
                .apply(lambda x: x.as_posix()).tolist()
            expected = sorted(expected)

            data = Database(root, [Spec001, Spec002]).update().data
            result = data.filepath.tolist()
            result = sorted(result)
            self.assertEqual(result, expected)

            result = data.groupby('asset_path').asset_valid.first().tolist()
            expected = [True, True, False, True, False]
            self.assertEqual(result, expected)

    def test_update_exclude(self):
        with TemporaryDirectory() as root:
            Spec001, Spec002, BadSpec = self.get_specifications()

            expected = self.create_files(root).filepath\
                .apply(lambda x: x.as_posix()).tolist()
            regex = r'misc\.txt|vdb'
            expected = list(filter(lambda x: not re.search(regex, x), expected))
            expected = sorted(expected)

            result = Database(root, [Spec001, Spec002], exclude_regex=regex)\
                .update().data.filepath.tolist()
            result = sorted(result)
            self.assertEqual(result, expected)

    def test_update_include(self):
        with TemporaryDirectory() as root:
            Spec001, Spec002, BadSpec = self.get_specifications()

            expected = self.create_files(root).filepath\
                .apply(lambda x: x.as_posix()).tolist()
            regex = r'misc\.txt|vdb'
            expected = list(filter(lambda x: re.search(regex, x), expected))
            expected = sorted(expected)

            result = Database(root, [Spec001, Spec002], include_regex=regex)\
                .update().data.filepath.tolist()
            result = sorted(result)
            self.assertEqual(result, expected)

    def test_update_include_exclude(self):
        Spec001, Spec002, BadSpec = self.get_specifications()

        with TemporaryDirectory() as root:
            expected = self.create_files(root).filepath\
                .apply(lambda x: x.as_posix()).tolist()
            i_regex = r'pizza'
            expected = list(filter(lambda x: re.search(i_regex, x), expected))
            e_regex = r'misc\.txt|vdb'
            expected = list(filter(lambda x: not re.search(e_regex, x), expected))
            expected = sorted(expected)

            result = Database(
                root,
                [Spec001, Spec002],
                include_regex=i_regex,
                exclude_regex=e_regex,
            )
            result = result.update().data.filepath.tolist()
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

            keys = files.filepath.tolist()
            lut = dict(zip(keys, files.file_error.tolist()))

            data = data[data.filepath.apply(lambda x: x in keys)]

            regexes = data.filepath.apply(lambda x: lut[x.as_posix()]).tolist()
            results = data.file_error.apply(lambda x: x[0]).tolist()
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

    # FILE-METHODS--------------------------------------------------------------
    def test_validate_filepath(self):
        data = self.get_data('/tmp')

        error = 'Invalid asset directory name'
        mask = data.file_error == error
        data.loc[mask, 'file_error'] = np.nan

        cols = ['specification_class', 'filepath', 'file_error']
        data = data[cols]

        Database._validate_filepath(data)
        result = data.loc[mask, 'file_error'].tolist()[0]
        self.assertRegex(result, error)

    def test_add_file_traits(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        data = [
            [
                Spec001,
                '/tmp/p-proj001_s-spec001_d-desc_v001_c000-000_f0001.png',
                np.nan,
                'proj001', 'spec001', 'desc', 1, [0, 0], 1, 'png'
            ],
            [
                Spec001,
                '/tmp/p-proj001_s-spec001_d-desc_v001_c000-000_f0002.png',
                np.nan,
                'proj001', 'spec001', 'desc', 1, [0, 0], 2, 'png'
            ],
            [
                Spec002,
                '/tmp/p-proj002_s-spec002_d-MASTER_v001_f0001.png',
                'file_Error',
                np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan
            ],
            [
                Spec002,
                '/tmp/p-proj002_s-spec002_d-desc_v001_f0002.png',
                np.nan,
                'proj002', 'spec002', 'desc', 1, np.nan, 2, 'png'
            ],
            [
                np.nan,
                '/tmp/misc.txt',
                'file_Error',
                np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan
            ],
        ]
        data = DataFrame(data)
        cols = [
            'project', 'specification', 'descriptor', 'version', 'coordinate',
            'frame', 'extension'
        ]
        data.columns = ['specification_class', 'filepath', 'file_error'] + cols
        temp = data.copy()

        Database._add_file_traits(data)
        for col in cols:
            result = data[col].fillna('null').tolist()
            expected = temp[col].fillna('null').tolist()
            self.assertEqual(result, expected)

    # ASSET-METHODS-------------------------------------------------------------
    def test_add_asset_traits(self):
        data = DataFrame()
        data['asset_path'] = ['a', 'a', 'b', 'b', np.nan]
        data['file_traits'] = [
            dict(w=0, x=1, y=1),
            dict(x=2, y=2),
            dict(x=1, y=1, z=1),
            dict(x=2, y=2, z=2),
            {},
        ]
        Database._add_asset_traits(data)
        result = data.asset_traits.tolist()
        expected = [
            dict(w=[0], x=[1, 2], y=[1, 2]),
            dict(w=[0], x=[1, 2], y=[1, 2]),
            dict(x=[1, 2], y=[1, 2], z=[1, 2]),
            dict(x=[1, 2], y=[1, 2], z=[1, 2]),
            {}
        ]
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
                'file_Error',
            ],
            [
                Spec002,
                '/tmp/p-proj002_s-spec002_d-desc_v001/p-proj002_s-spec002_d-desc_v001_f0002.png',
                np.nan,
            ],
            [
                np.nan,
                '/tmp/proj002/misc.txt',
                'file_Error',
            ],
        ]

        data = DataFrame(data)
        data.columns = ['specification_class', 'filepath', 'file_error']

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
                'file_Error',
            ],
            [
                Spec002,
                '/tmp/p-proj002_s-spec002_d-desc_v001/p-proj002_s-spec002_d-desc_v001_f0002.png',
                np.nan,
            ],
            [
                np.nan,
                '/tmp/proj002/misc.txt',
                'file_Error',
            ],
        ]

        data = DataFrame(data)
        data.columns = ['specification_class', 'filepath', 'file_error']

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
                'file_Error',
            ],
            [
                Spec002,
                '/tmp/p-proj002_s-spec002_d-desc_v001/p-proj002_s-spec002_d-desc_v001_f0002.png',
                np.nan,
            ],
            [
                np.nan,
                '/tmp/proj002/misc.txt',
                'file_Error',
            ],
        ]

        data = DataFrame(data)
        data.columns = ['specification_class', 'filepath', 'file_error']
        expected = data.filepath\
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

        data['filepath'] = [np.nan, Path('/foo/bar'), Path('/bar/foo')]
        data['version'] = [1, 2, 3]
        expected = [np.nan, '/foo/bar', '/bar/foo']
        result = Database._cleanup(data).filepath.tolist()
        self.assertEqual(result, expected)

        result = Database._cleanup(data).columns.tolist()
        self.assertEqual(result, self.columns)

    def test_validate_assets(self):
        with TemporaryDirectory() as root:
            Spec001, Spec002, BadSpec = self.get_specifications()
            data = self.create_files(root).head(1)
            traits = dict(
                project=['proj001'],
                specification=['spec001'],
                descriptor=['desc'],
                version=[1],
                coordinate=[[0, 1]],
                frame=[5],
                extension=['png'],
                height=[5],
                width=[4],
                channels=[3],
            )
            data['asset_traits'] = [traits]
            Database._validate_assets(data)

            for i, row in data.iterrows():
                self.assertTrue(np.isnan(row.asset_error))
                self.assertTrue(row.asset_valid)

            result = data.columns.tolist()
            cols = ['asset_error', 'asset_valid']
            for expected in cols:
                self.assertIn(expected, result)

    def test_validate_assets_invalid_one_file(self):
        with TemporaryDirectory() as root:
            Spec001, Spec002, BadSpec = self.get_specifications()
            data = self.create_files(root).head(1)
            traits = dict(
                project=['proj001'],
                specification=['spec001'],
                descriptor=['desc'],
                version=[1],
                coordinate=[[0, 1]],
                frame=[5],
                extension=['png'],
                height=[5],
                width=[40],
                channels=[3],
            )
            data['asset_traits'] = [traits]
            Database._validate_assets(data)

            for i, row in data.iterrows():
                self.assertRegex(row.asset_error, '40 != 4')
                self.assertFalse(row.asset_valid)

    def test_validate_assets_invalid_many_file(self):
        with TemporaryDirectory() as root:
            Spec001, Spec002, BadSpec = self.get_specifications()
            data = self.create_files(root).head(2)
            traits = dict(
                project=['proj001', 'proj001'],
                specification=['spec001', 'spec001'],
                descriptor=['desc', 'desc'],
                version=[1, 1],
                coordinate=[[0, 1], [0, 1]],
                frame=[5, 5],
                extension=['png', 'png'],
                height=[5, 5],
                width=[4, 400],
                channels=[3, 3],
            )
            data['asset_traits'] = [traits, traits]
            Database._validate_assets(data)

            for i, row in data.iterrows():
                self.assertRegex(row.asset_error, '400 != 4')
                self.assertFalse(row.asset_valid)
