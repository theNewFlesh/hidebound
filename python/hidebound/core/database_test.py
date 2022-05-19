from copy import copy
import json
from itertools import chain
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import re

from moto import mock_s3
from schematics.exceptions import DataError
import boto3 as boto

from hidebound.core.database import Database
from hidebound.core.database_test_base import DatabaseTestBase
from hidebound.exporters.mock_girder import MockGirderExporter
import hidebound.core.tools as hbt
# ------------------------------------------------------------------------------


class DatabaseTests(DatabaseTestBase):
    def write_spec_file(self, root):
        os.makedirs(Path(root, 'specs'))
        spec_file = Path(root, 'specs', 'specs.py').as_posix()

        text = '''
            from schematics.types import IntType, ListType, StringType
            from hidebound.core.specification_base import SpecificationBase

            class Spec001(SpecificationBase):
                foo = ListType(IntType(), required=True)
                bar = ListType(StringType(), required=True)

            class Spec002(SpecificationBase):
                boo = ListType(IntType(), required=True)
                far = ListType(StringType(), required=True)

            SPECIFICATIONS = [Spec001, Spec002]'''
        text = re.sub('            ', '', text)
        with open(spec_file, 'w') as f:
            f.write(text)

        return spec_file

    def test_from_config(self):
        with TemporaryDirectory() as root:
            # create hb root dir
            hb_root = Path(root, 'hidebound').as_posix()
            os.makedirs(hb_root)
            spec_file = self.write_spec_file(root)

            config = dict(
                root_directory=root,
                hidebound_directory=hb_root,
                specification_files=[spec_file],
                include_regex='foo',
                exclude_regex='bar',
                write_mode='copy',
            )
            expected = copy(config)
            Database.from_config(config)
            self.assertEqual(config, expected)

            config['specification_files'] = ['/foo/bar.py']
            with self.assertRaises(DataError):
                Database.from_config(config)

    def test_from_json(self):
        with TemporaryDirectory() as root:
            # create hb root dir
            hb_root = Path(root, 'hidebound').as_posix()
            os.makedirs(hb_root)
            spec_file = self.write_spec_file(root)

            config = dict(
                root_directory=root,
                hidebound_directory=hb_root,
                specification_files=[spec_file],
                include_regex='foo',
                exclude_regex='bar',
                write_mode='copy',
            )
            config_file = Path(root, 'config.json')
            with open(config_file, 'w') as f:
                json.dump(config, f)

            Database.from_json(config_file)

    def test_init(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        with TemporaryDirectory() as root:
            root = Path(root, 'projects')
            os.makedirs(root)

            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)

            self.create_files(root)
            Database(root, hb_root)
            Database(root, hb_root, [Spec001])
            Database(root, hb_root, [Spec001, Spec002])

    def test_init_bad_root(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)
            expected = '/foo is not a directory or does not exist'
            with self.assertRaisesRegexp(FileNotFoundError, expected):
                Database('/foo', hb_root, [Spec001])

    def test_init_bad_hb_root(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            expected = '/hidebound is not a directory or does not exist'
            with self.assertRaisesRegexp(FileNotFoundError, expected):
                Database(root, hb_root)

            temp = Path(root, 'Hidebound')
            os.makedirs(temp)
            expected = r'Hidebound directory is not named hidebound\.$'
            with self.assertRaisesRegexp(NameError, expected):
                Database(root, temp)

    def test_init_bad_specifications(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)

            self.create_files(root)
            expected = 'SpecificationBase may only contain subclasses of'
            expected += ' SpecificationBase. Found: .*.'

            with self.assertRaisesRegexp(TypeError, expected):
                Database(root, hb_root, [BadSpec])

            with self.assertRaisesRegexp(TypeError, expected):
                Database(root, hb_root, [Spec001, BadSpec])

    def test_init_bad_write_mode(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)

            expected = r"Invalid write mode: foo not in \['copy', 'move'\]\."
            with self.assertRaisesRegexp(ValueError, expected):
                Database(root, hb_root, [Spec001], write_mode='foo')

    # CREATE--------------------------------------------------------------------
    def test_create(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)
            Spec001, Spec002, BadSpec = self.get_specifications()
            self.create_files(root)

            db = Database(root, hb_root, [Spec001, Spec002])

            # test data initiliazation error
            expected = 'Data not initialized. Please call update.'
            with self.assertRaisesRegexp(RuntimeError, expected):
                db.create()

            db.update()
            data = db.data
            db.create()

            data = data[data.asset_valid]

            # ensure files are written
            result = Path(hb_root, 'content')
            result = hbt.directory_to_dataframe(result)
            result = sorted(result.filename.tolist())
            self.assertGreater(len(result), 0)
            expected = sorted(data.filename.tolist())
            self.assertEqual(result, expected)

            # ensure file metadata is written
            result = len(os.listdir(Path(hb_root, 'metadata', 'file')))
            self.assertGreater(result, 0)
            expected = data.filepath.nunique()
            self.assertEqual(result, expected)

            # ensure asset metadata is written
            result = len(os.listdir(Path(hb_root, 'metadata', 'asset')))
            self.assertGreater(result, 0)
            expected = data.asset_path.nunique()
            self.assertEqual(result, expected)

            # ensure asset chunk is written
            result = len(os.listdir(Path(hb_root, 'metadata', 'asset-chunk')))
            self.assertEqual(result, 1)

            # ensure file chunk is written
            result = len(os.listdir(Path(hb_root, 'metadata', 'file-chunk')))
            self.assertEqual(result, 1)

    def test_create_all_invalid(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)
            Spec001, Spec002, BadSpec = self.get_specifications()
            self.create_files(root)

            db = Database(root, hb_root, [Spec001, Spec002])
            db.update()
            data = db.data
            data['asset_valid'] = False
            db.create()

            result = Path(hb_root, 'content')
            self.assertFalse(result.exists())

            result = Path(hb_root, 'metadata', 'file')
            self.assertFalse(result.exists())

            result = Path(hb_root, 'metadata', 'asset')
            self.assertFalse(result.exists())

    def test_create_copy(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)

            root = Path(root, 'projects').as_posix()
            os.makedirs(root)

            Spec001, Spec002, BadSpec = self.get_specifications()

            expected = self.create_files(root).filepath\
                .apply(lambda x: x.as_posix()).tolist()
            expected = sorted(expected)

            db = Database(root, hb_root, [Spec001, Spec002], write_mode='copy')
            db.update()
            db.create()

            result = hbt.directory_to_dataframe(root).filepath.tolist()
            result = sorted(result)
            self.assertEqual(result, expected)

    def test_create_move(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)

            root = Path(root, 'projects').as_posix()
            os.makedirs(root)

            self.create_files(root)
            Spec001, Spec002, BadSpec = self.get_specifications()
            db = Database(root, hb_root, [Spec001, Spec002], write_mode='move')
            db.update()
            data = db.data
            db.create()
            data = data[data.asset_valid]

            # assert that no valid asset files are found in their original
            result = data.filepath.apply(lambda x: os.path.exists(x)).unique().tolist()
            self.assertEqual(result, [False])

            # ensure files are written
            result = Path(hb_root, 'content')
            result = hbt.directory_to_dataframe(result)
            result = sorted(result.filename.tolist())
            self.assertGreater(len(result), 0)
            expected = sorted(data.filename.tolist())
            self.assertEqual(result, expected)

            # ensure file metadata is written
            result = len(os.listdir(Path(hb_root, 'metadata', 'file')))
            self.assertGreater(result, 0)
            expected = data.filepath.nunique()
            self.assertEqual(result, expected)

            # ensure asset metadata is written
            result = len(os.listdir(Path(hb_root, 'metadata', 'asset')))
            self.assertGreater(result, 0)
            expected = data.asset_path.nunique()
            self.assertEqual(result, expected)

    # READ----------------------------------------------------------------------
    def test_read_legal_types(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)

            root = Path(root, 'projects')
            os.makedirs(root)

            self.create_files(root)
            db = Database(root, hb_root, [Spec001, Spec002])

            # test data initiliazation error
            expected = 'Data not initialized. Please call update.'
            with self.assertRaisesRegexp(RuntimeError, expected):
                db.read()

            db.update()
            data = db.read()

            # test types by file
            result = data.applymap(type)\
                .apply(lambda x: x.unique().tolist())\
                .tolist()
            result = list(chain(*result))
            result = set(result)

            expected = set([int, float, str, bool, None])
            result = result.difference(expected)
            self.assertEqual(len(result), 0)

            # test types by asset
            data = db.read(group_by_asset=True)
            result = data.applymap(type)\
                .apply(lambda x: x.unique().tolist()) \
                .loc[0].tolist()
            result = set(result)

            expected = set([int, float, str, bool, None])
            result = result.difference(expected)
            self.assertEqual(len(result), 0)

    def test_read_traits(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)

            root = Path(root, 'projects')
            os.makedirs(root)

            self.create_files(root)
            db = Database(root, hb_root, [Spec001, Spec002])
            db.update()

            # test file traits
            db.data.file_traits = db.data.file_traits\
                .apply(lambda x: {'foo': 'bar', 'illegal': set()})
            data = db.read()

            result = data.columns
            self.assertIn('foo', result)
            self.assertNotIn('illegal', result)

            # test asset traits
            db.update()

            db.data.asset_traits = db.data.asset_traits\
                .apply(lambda x: {'foo': 'bar', 'illegal': set()})
            data = db.read(group_by_asset=True)

            result = data.columns
            self.assertIn('foo', result)
            self.assertNotIn('illegal', result)

    def test_read_coordinates(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)

            root = Path(root, 'projects')
            os.makedirs(root)

            self.create_files(root)
            db = Database(root, hb_root, [Spec001, Spec002])
            db.update()

            db.data.file_traits = db.data.file_traits\
                .apply(lambda x: {'coordinate': [0, 1]})
            data = db.read()

            # xy
            result = data.columns
            expected = ['coordinate_x', 'coordinate_y']
            for col in expected:
                self.assertIn(col, result)
            self.assertNotIn('coordinate_z', result)

            # xyz
            db.update()

            db.data.file_traits = db.data.file_traits\
                .apply(lambda x: {'coordinate': [0, 1, 0]})
            data = db.read()

            result = data.columns
            expected = ['coordinate_x', 'coordinate_y', 'coordinate_z']
            for col in expected:
                self.assertIn(col, result)

    def test_read_column_order(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)

            root = Path(root, 'projects')
            os.makedirs(root)

            self.create_files(root)
            db = Database(root, hb_root, [Spec001, Spec002])
            db.update()

            result = db.read().columns.tolist()
            expected = [
                'project',
                'specification',
                'descriptor',
                'version',
                'coordinate_x',
                'coordinate_y',
                'coordinate_z',
                'frame',
                'extension',
                'filename',
                'filepath',
                'file_error',
                'asset_name',
                'asset_path',
                'asset_type',
                'asset_error',
                'asset_valid'
            ]
            expected = list(filter(lambda x: x in result, expected))
            result = result[:len(expected)]
            self.assertEqual(result, expected)

    def test_read_no_files(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)

            root = Path(root, 'projects')
            os.makedirs(root)

            db = Database(root, hb_root, [Spec001, Spec002])

            db.update()
            result = db.read()
            self.assertEqual(len(result), 0)

        # UPDATE--------------------------------------------------------------------
    def test_update(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)
            Spec001, Spec002, BadSpec = self.get_specifications()

            expected = self.create_files(root).filepath\
                .apply(lambda x: x.as_posix()).tolist()
            expected = sorted(expected)

            data = Database(root, hb_root, [Spec001, Spec002]).update().data
            result = data.filepath.tolist()
            result = list(filter(lambda x: 'progress' not in x, result))
            result = sorted(result)
            self.assertEqual(result, expected)

            result = data.groupby('asset_path').asset_valid.first().tolist()
            expected = [True, True, False, True, False]
            self.assertEqual(result, expected)

    def test_update_exclude(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)
            Spec001, Spec002, BadSpec = self.get_specifications()

            expected = self.create_files(root).filepath\
                .apply(lambda x: x.as_posix()).tolist()
            regex = r'misc\.txt|vdb'
            expected = list(filter(lambda x: not re.search(regex, x), expected))
            expected = sorted(expected)

            result = Database(root, hb_root, [Spec001, Spec002], exclude_regex=regex)\
                .update().data.filepath.tolist()
            result = list(filter(lambda x: 'progress' not in x, result))
            result = sorted(result)
            self.assertEqual(result, expected)

    def test_update_include(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)
            Spec001, Spec002, BadSpec = self.get_specifications()

            expected = self.create_files(root).filepath\
                .apply(lambda x: x.as_posix()).tolist()
            regex = r'misc\.txt|vdb'
            expected = list(filter(lambda x: re.search(regex, x), expected))
            expected = sorted(expected)

            result = Database(root, hb_root, [Spec001, Spec002], include_regex=regex)\
                .update().data.filepath.tolist()
            result = sorted(result)
            self.assertEqual(result, expected)

    def test_update_include_exclude(self):
        Spec001, Spec002, BadSpec = self.get_specifications()

        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)

            expected = self.create_files(root).filepath\
                .apply(lambda x: x.as_posix()).tolist()
            i_regex = r'pizza'
            expected = list(filter(lambda x: re.search(i_regex, x), expected))
            e_regex = r'misc\.txt|vdb'
            expected = list(filter(lambda x: not re.search(e_regex, x), expected))
            expected = sorted(expected)

            result = Database(
                root,
                hb_root,
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
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)
            result = Database(root, hb_root, [Spec001]).update().data
            self.assertEqual(len(result), 0)
            self.assertEqual(result.columns.tolist(), self.columns)

    def test_update_error(self):
        Spec001, Spec002, BadSpec = self.get_specifications()

        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)
            files = self.create_files(root)
            data = Database(root, hb_root, [Spec001, Spec002]).update().data

            keys = files.filepath.tolist()
            lut = dict(zip(keys, files.file_error.tolist()))

            data = data[data.filepath.apply(lambda x: x in keys)]

            regexes = data.filepath.apply(lambda x: lut[x.as_posix()]).tolist()
            results = data.file_error.apply(lambda x: x[0]).tolist()
            for result, regex in zip(results, regexes):
                self.assertRegex(result, regex)

    # DELETE--------------------------------------------------------------------
    def test_delete(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)

            data_dir = Path(hb_root, 'content')
            os.makedirs(data_dir)

            meta_dir = Path(hb_root, 'metadata')
            os.makedirs(meta_dir)

            root = Path(root, 'projects')
            os.makedirs(root)

            self.create_files(root)
            expected = hbt.directory_to_dataframe(root).filepath.tolist()
            expected = sorted(expected)

            db = Database(root, hb_root, [])
            db.delete()

            self.assertFalse(data_dir.exists())
            self.assertFalse(meta_dir.exists())

            result = hbt.directory_to_dataframe(root).filepath.tolist()
            result = sorted(result)
            self.assertEqual(result, expected)

    # EXPORT--------------------------------------------------------------------
    def test_export_girder(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)
            Spec001, Spec002, _ = self.get_specifications()
            self.create_files(root)

            exporters = dict(girder=dict(api_key='api_key', root_id='root_id'))
            db = Database(
                root, hb_root, [Spec001, Spec002], exporters=exporters
            )
            db._Database__exporter_lut = dict(girder=MockGirderExporter)

            db.update().create().export()

            client = db._Database__exporter_lut['girder']._client
            result = list(client.folders.keys())
            asset_paths = [
                'p-proj001_s-spec001_d-pizza_v001',
                'p-proj001_s-spec001_d-pizza_v002',
                'p-proj001_s-spec002_d-taco_v001',
            ]
            for expected in asset_paths:
                self.assertIn(expected, result)

    @mock_s3
    def test_export_s3(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)
            Spec001, Spec002, _ = self.get_specifications()
            data = self.create_files(root)

            exporters = dict(
                s3=dict(
                    access_key='foo',
                    secret_key='bar',
                    bucket='bucket',
                    region='us-west-2',
                )
            )
            db = Database(
                root, hb_root, [Spec001, Spec002], exporters=exporters
            )

            db.update().create().export()

            results = boto.session \
                .Session(
                    aws_access_key_id='foo',
                    aws_secret_access_key='bar',
                    region_name='us-west-2',
                ) \
                .resource('s3') \
                .Bucket('bucket') \
                .objects.all()
            results = [x.key for x in results]

            # content
            data = data[data.asset_valid]
            expected = data.filepath.apply(lambda x: Path(*x.parts[3:])).tolist()
            expected = sorted([f'hidebound/content/{x}' for x in expected])
            content = sorted(list(filter(
                lambda x: re.search('content', x), results
            )))
            self.assertEqual(content, expected)

            # asset metadata
            expected = data.asset_path.nunique()
            result = len(list(filter(
                lambda x: re.search('metadata/asset/', x), results
            )))
            self.assertEqual(result, expected)

            # file metadata
            result = len(list(filter(
                lambda x: re.search('metadata/file/', x), results
            )))
            self.assertEqual(result, len(content))

            # asset chunk
            result = len(list(filter(
                lambda x: re.search('metadata/asset-chunk/', x), results
            )))
            self.assertEqual(result, 1)

            # file chunk
            result = len(list(filter(
                lambda x: re.search('metadata/file-chunk/', x), results
            )))
            self.assertEqual(result, 1)

    def test_export_local_disk(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)
            Spec001, Spec002, _ = self.get_specifications()
            self.create_files(root)

            target = Path(root, 'target').as_posix()
            os.makedirs(target)
            exporters = dict(local_disk=dict(target_directory=target))

            db = Database(
                root, hb_root, [Spec001, Spec002], exporters=exporters
            )

            db.update().create()
            self.assertEqual(len(os.listdir(target)), 0)
            db.export()

            expected = hbt.directory_to_dataframe(hb_root).filepath
            mask = expected \
                .apply(lambda x: re.search('/(asset|file|content)', x)) \
                .astype(bool)
            expected = expected[mask] \
                .apply(lambda x: re.sub('.*/hidebound/', '', x)) \
                .tolist()
            expected = sorted(expected)

            result = hbt.directory_to_dataframe(target).filepath \
                .apply(lambda x: re.sub('.*/target/', '', x)) \
                .tolist()
            result = sorted(result)

            self.assertEqual(result, expected)

    # SEARCH--------------------------------------------------------------------
    def test_search(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)

            root = Path(root, 'projects')
            os.makedirs(root)

            self.create_files(root)
            db = Database(root, hb_root, [Spec001, Spec002])
            db.update()
            db.search('SELECT * FROM data WHERE version == 3')

    # WEBHOOKS
    def test_call_webhooks(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound').as_posix()
            os.makedirs(hb_root)
            spec_file = self.write_spec_file(root)
            self.create_files(root)

            config = dict(
                root_directory=root,
                hidebound_directory=hb_root,
                specification_files=[spec_file],
                include_regex='foo',
                exclude_regex='bar',
                write_mode='copy',
                webhooks=[
                    {
                        'url': 'http://foobar.com/api/user?',
                        'method': 'get',
                        'headers': {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json',
                        },
                        'timeout': 10,
                        'params': {
                            'foo': 'bar'
                        }
                    },
                    {
                        'url': 'http://foobar.com/api/user?',
                        'method': 'post',
                        'headers': {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json',
                        },
                        'data': {
                            'id': '123',
                            'name': 'john',
                            'other': {'stuff': 'things'}
                        },
                        'json': {
                            'foo': 'bar'
                        }
                    }
                ]
            )

            db = Database.from_config(config)
            for response in db.call_webhooks():
                self.assertEqual(response.status_code, 403)


class DatabaseDaskTests(DatabaseTestBase):
    def test_update_dask(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hidebound')
            os.makedirs(hb_root)
            Spec001, Spec002, BadSpec = self.get_specifications()

            expected = self.create_files(root).filepath\
                .apply(lambda x: x.as_posix()).tolist()
            expected = sorted(expected)

            data = Database(
                root, hb_root, [Spec001, Spec002],
                dask_enabled=True, dask_partitions=2,
            ).update().data
            result = data.filepath.tolist()
            result = list(filter(lambda x: 'progress' not in x, result))
            result = sorted(result)
            self.assertEqual(result, expected)

            result = data.groupby('asset_path').asset_valid.first().tolist()
            expected = [True, True, False, True, False]
            self.assertEqual(result, expected)
