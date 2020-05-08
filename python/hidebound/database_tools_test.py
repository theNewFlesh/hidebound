import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
from pandas import DataFrame
import numpy as np

from hidebound.database_test_base import DatabaseTestBase
from hidebound.specification_base import ComplexSpecificationBase
from hidebound.specification_base import FileSpecificationBase
from hidebound.specification_base import SequenceSpecificationBase
import hidebound.database_tools as db_tools
import hidebound.tools as tools
# ------------------------------------------------------------------------------


class DatabaseTests(DatabaseTestBase):
    # SPECIFICATION-FUNCTIONS---------------------------------------------------
    def test_add_specification(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        specs = {Spec001.name: Spec001, Spec002.name: Spec002}

        data = self.get_directory_to_dataframe_data('/tmp')
        db_tools._add_specification(data, specs)

        result = data.specification.tolist()
        expected = data.specification
        self.assertEqual(result, expected.tolist())

    # FILE-FUNCTIONS------------------------------------------------------------
    def test_validate_filepath(self):
        data = self.get_data('/tmp')

        error = 'Invalid asset directory name'
        mask = data.file_error == error
        data.loc[mask, 'file_error'] = np.nan

        cols = ['specification_class', 'filepath', 'file_error']
        data = data[cols]

        db_tools._validate_filepath(data)
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

        db_tools._add_file_traits(data)
        for col in cols:
            result = data[col].fillna('null').tolist()
            expected = temp[col].fillna('null').tolist()
            self.assertEqual(result, expected)

    # ASSET-FUNCTIONS-----------------------------------------------------------
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
        db_tools._add_asset_traits(data)
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

        db_tools._add_asset_id(data)
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

        db_tools._add_asset_name(data)
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

        db_tools._add_asset_path(data)
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
        db_tools._add_asset_type(data)
        result = data['asset_type'].fillna('null').tolist()
        expected = ['file', 'sequence', 'complex', 'null']
        self.assertEqual(result, expected)

    def test_cleanup(self):
        data = DataFrame()
        result = db_tools._cleanup(data).columns.tolist()
        self.assertEqual(result, self.columns)

        data['filepath'] = [np.nan, Path('/foo/bar'), Path('/bar/foo')]
        data['version'] = [1, 2, 3]
        expected = [np.nan, '/foo/bar', '/bar/foo']
        result = db_tools._cleanup(data).filepath.tolist()
        self.assertEqual(result, expected)

        result = db_tools._cleanup(data).columns.tolist()
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
            db_tools._validate_assets(data)

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
            db_tools._validate_assets(data)

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
            db_tools._validate_assets(data)

            for i, row in data.iterrows():
                self.assertRegex(row.asset_error, '400 != 4')
                self.assertFalse(row.asset_valid)

    def test_get_data_for_write(self):
        data = tools.relative_path(__file__, '../../resources/fake_data.csv')
        data = pd.read_csv(data)

        file_data, file_meta, asset_meta = db_tools._get_data_for_write(
            data,
            '/tmp/projects',
            '/tmp/hidebound'
        )

        data = data[data.asset_valid]

        expected = data.shape[0]
        self.assertEqual(file_data.shape[0], expected)
        self.assertEqual(file_meta.shape[0], expected)

        expected = data.asset_path.nunique()
        self.assertEqual(asset_meta.shape[0], expected)

        expected = set(data.filename.tolist())
        result = file_data.target.apply(lambda x: Path(x).name).tolist()
        result = set(result)
        self.assertEqual(result, expected)

        file_meta.metadata.apply(json.dumps)
        asset_meta.metadata.apply(json.dumps)

        result = file_data.source\
            .apply(lambda x: '/tmp/projects' in x).unique().tolist()
        self.assertEqual(result, [True])

        for item in [file_data, file_meta, asset_meta]:
            result = item.target\
                .apply(lambda x: '/tmp/hidebound' in x).unique().tolist()
            self.assertEqual(result, [True])

    def test_get_data_for_write_dirs(self):
        data = tools.relative_path(__file__, '../../resources/fake_data.csv')
        data = pd.read_csv(data)

        file_data, file_meta, asset_meta = db_tools._get_data_for_write(
            data,
            '/tmp/projects',
            '/tmp/hidebound'
        )

        result = file_data.target\
            .apply(lambda x: '/tmp/hidebound/data' in x).unique().tolist()
        self.assertEqual(result, [True])

        result = file_meta.target\
            .apply(lambda x: '/tmp/hidebound/metadata/file' in x).unique().tolist()
        self.assertEqual(result, [True])

        result = asset_meta.target\
            .apply(lambda x: '/tmp/hidebound/metadata/asset' in x).unique().tolist()
        self.assertEqual(result, [True])

    def test_get_data_for_write_empty_dataframe(self):
        data = DataFrame()
        data['asset_valid'] = [False, False]

        result = db_tools._get_data_for_write(
            data, '/tmp/projects', '/tmp/hidebound'
        )
        self.assertIs(result, None)

    def test_get_data_for_write_asset_id_file_ids_pair(self):
        data = tools.relative_path(__file__, '../../resources/fake_data.csv')
        data = pd.read_csv(data)

        file_data, file_meta, asset_meta = db_tools._get_data_for_write(
            data,
            '/tmp/projects',
            '/tmp/hidebound'
        )

        a = asset_meta
        a['asset_id'] = a.metadata.apply(lambda x: x['asset_id'])
        a['file_ids'] = a.metadata.apply(lambda x: x['file_ids'])
        keys = sorted(a.asset_id.tolist())
        vals = sorted(a.file_ids.tolist())
        a = dict(zip(keys, vals))

        b = file_meta
        b['asset_id'] = b.metadata.apply(lambda x: x['asset_id'])
        b['file_ids'] = b.metadata.apply(lambda x: x['file_id'])
        b = b.groupby('asset_id', as_index=False).agg(lambda x: x.tolist())
        keys = sorted(b.asset_id.tolist())
        vals = sorted(b.file_ids.tolist())
        b = dict(zip(keys, vals))

        self.assertEqual(a, b)
