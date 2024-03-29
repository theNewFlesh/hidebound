import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from girder_client import HttpError
from schematics.exceptions import DataError
import pytest

from hidebound.exporters.girder_exporter import GirderConfig, GirderExporter
from hidebound.exporters.mock_girder import MockGirderClient
# ------------------------------------------------------------------------------


RERUNS = 3


class GirderConfigTests(unittest.TestCase):
    def setUp(self):
        self.config = dict(
            name='girder',
            api_key='api_key',
            root_id='root_id',
            root_type='collection',
            host='http://0.0.0.0',
            port=8180,
        )

    def test_validate(self):
        config = self.config
        GirderConfig(config).validate()
        config['root_type'] = 'folder'
        GirderConfig(config).validate()

    def test_name(self):
        del self.config['name']
        with self.assertRaises(DataError):
            GirderConfig(self.config).validate()

        self.config['name'] = 'foobar'
        with self.assertRaises(DataError):
            GirderConfig(self.config).validate()

    def test_root_type(self):
        config = self.config
        expected = r"foo is not in \[\'collection\', \'folder\'\]"
        config['root_type'] = 'foo'
        with self.assertRaisesRegex(DataError, expected):
            GirderConfig(config).validate()

    def test_host(self):
        config = self.config
        expected = 'Not a well-formed URL'
        config['host'] = '0.1.2'
        with self.assertRaisesRegex(DataError, expected):
            GirderConfig(config).validate()

        config['host'] = 'foo.bar.com'
        with self.assertRaisesRegex(DataError, expected):
            GirderConfig(config).validate()

        config = self.config
        del config['host']
        result = GirderConfig(config).to_primitive()['host']
        self.assertEqual(result, 'http://0.0.0.0')

    def test_port(self):
        config = self.config
        expected = '1023 !> 1023.'
        config['port'] = 1023
        with self.assertRaisesRegex(DataError, expected):
            GirderConfig(config).validate()

        expected = '65536 !< 65536.'
        config['port'] = 65536
        with self.assertRaisesRegex(DataError, expected):
            GirderConfig(config).validate()
# ------------------------------------------------------------------------------


class GirderExporterTests(unittest.TestCase):
    def setUp(self):
        self.client = MockGirderClient()
        self.config = dict(
            name='girder',
            api_key='api_key',
            root_id='root_id',
            root_type='collection',
            host='http://2.2.2.2',
            port=5555,
        )
        self.exporter = GirderExporter(**self.config, client=self.client)

    def create_data(self, root):
        data = Path(root, 'content')
        meta = Path(root, 'metadata')
        asset = Path(meta, 'asset')
        file_ = Path(meta, 'file')
        asset_chunk_path = Path(meta, 'asset-chunk')
        file_chunk_path = Path(meta, 'file-chunk')

        os.makedirs(data)
        os.makedirs(meta)
        os.makedirs(asset)
        os.makedirs(file_)
        os.makedirs(asset_chunk_path)
        os.makedirs(file_chunk_path)

        # create asset data
        asset_data = [
            dict(asset_type='file', file_ids=['1-1', '1-2', '1-3']),
            dict(asset_type='sequence', file_ids=['2-1', '2-2', '2-3']),
            dict(asset_type='sequence', file_ids=['3-1']),
            dict(asset_type='complex', file_ids=['4-1', '4-2', '4-3']),
        ]
        assets = []
        for i, data in enumerate(asset_data):
            id_ = i + 1
            meta_path = Path(asset, f'{id_}.json')
            data['asset_path'] = f'{root}/content/{id_}'
            data['asset_path_relative'] = f'{id_}'
            data['asset_name'] = f'{id_}'
            assets.append([meta_path, data])

        # create file data
        ids = [
            '1-1', '1-2', '1-3', '2-1', '2-2', '2-3', '3-1', '4-1', '4-2', '4-3'
        ]
        files = []
        for id_ in ids:
            metapath = Path(file_, f'{id_}.json')

            pid = id_.split('-')[0]
            data = dict(
                filepath=f'{root}/content/{pid}/{id_}.txt',
                filepath_relative=f'{pid}/{id_}.txt',
                filename=f'{id_}.txt',
                foo=f'bar-{id_}'
            )
            files.append([metapath, data])

        for filepath, data in assets:
            with open(filepath, 'w') as f:
                json.dump(data, f)

        for filepath, data in files:
            with open(filepath, 'w') as f:
                json.dump(data, f)

            temp = data['filepath']
            os.makedirs(Path(temp).parent, exist_ok=True)
            with open(temp, 'w') as f:
                f.write('')

        # write asset chunk
        asset_chunk = [json.dumps(x[1]) for x in assets]
        asset_chunk = '[\n' + ',\n'.join(asset_chunk) + ']'
        asset_chunk_path = Path(
            asset_chunk_path, 'hidebound-asset-chunk_01-01-01T01-01-01.json'
        )
        with open(asset_chunk_path, 'w') as f:
            f.write(asset_chunk)

        # write file chunk
        file_chunk = [json.dumps(x[1]) for x in files]
        file_chunk = '[\n' + ',\n'.join(file_chunk) + ']'
        file_chunk_path = Path(
            file_chunk_path, 'hidebound-file-chunk_01-01-01T01-01-01.json'
        )
        with open(file_chunk_path, 'w') as f:
            f.write(file_chunk)

        return assets, files, asset_chunk, file_chunk

    def test_from_config(self):
        GirderExporter.from_config(self.config, client=self.client)
        self.config['root_type'] = 'taco'
        with self.assertRaises(DataError):
            GirderExporter.from_config(self.config, client=self.client)

    def test_init(self):
        result = GirderExporter(
            'api_key',
            'root_id',
            root_type='collection',
            host='http://1.2.3.4',
            port=5678,
            client=self.client
        )
        expected = 'http://1.2.3.4:5678/api/v1'
        self.assertEqual(result._url, expected)

    @pytest.mark.flaky(reruns=RERUNS)
    @pytest.mark.skipif('SKIP_SLOW_TESTS' in os.environ, reason='slow test')
    def test_export(self):
        with TemporaryDirectory() as root:
            self.client = MockGirderClient(add_suffix=False)

            e_assets, e_files, _, _ = self.create_data(root)
            e_assets = [x[1]['asset_name'] for x in e_assets]
            e_files = [x[1]['filename'] for x in e_files]

            GirderExporter\
                .from_config(self.config, client=self.client) \
                .export(root)

            result = self.client.folders.keys()
            result = sorted(list(result))
            self.assertEqual(result, e_assets)

            result = self.client.items.keys()
            result = sorted(list(result))
            self.assertEqual(result, e_files)

    @pytest.mark.flaky(reruns=RERUNS)
    @pytest.mark.skipif('SKIP_SLOW_TESTS' in os.environ, reason='slow test')
    def test_export_no_file_metadata(self):
        with TemporaryDirectory() as root:
            self.client = MockGirderClient(add_suffix=False)

            e_assets, e_files, _, _ = self.create_data(root)
            e_assets = [x[1]['asset_name'] for x in e_assets]
            e_files = [x[1]['filename'] for x in e_files]

            config = self.config
            config['metadata_types'] = ['asset']
            GirderExporter\
                .from_config(config, client=self.client) \
                .export(root)

            result = self.client.folders.keys()
            result = sorted(list(result))
            self.assertEqual(result, e_assets)

            result = self.client.items.keys()
            result = sorted(list(result))
            self.assertEqual(result, e_files)

    def test_export_dirs(self):
        dirpath = '/foo/bar/baz'
        meta = dict(foo='bar')
        self.exporter._export_dirs(dirpath, metadata=meta)

        result = sorted(self.client.folders.keys())
        self.assertEqual(result, ['bar', 'baz', 'foo'])

        result = self.client.folders
        self.assertIsNone(result['foo']['metadata'])
        self.assertIsNone(result['bar']['metadata'])
        self.assertEqual(result['baz']['metadata'], meta)

    def test_export_dirs_single_dir(self):
        dirpath = '/foo'
        expected = dict(foo='bar')
        self.exporter._export_dirs(dirpath, metadata=expected)
        result = self.client.folders

        self.assertEqual(list(result.keys()), ['foo'])
        self.assertEqual(result['foo']['metadata'], expected)

        with self.assertRaises(HttpError):
            self.exporter._export_dirs(
                dirpath, metadata=expected, exists_ok=False
            )

        expected = dict(pizza='bagel')
        self.exporter._export_dirs(dirpath, metadata=expected, exists_ok=True)
        result = self.client.folders
        self.assertEqual(result['foo (1)']['metadata'], expected)

    def test_export_dirs_exists_ok(self):
        dirpath = '/foo/bar/baz'
        meta = dict(foo='bar')
        self.exporter._export_dirs(dirpath, metadata=meta)

        # test exists_ok = False
        with self.assertRaises(HttpError):
            self.exporter._export_dirs(dirpath, exists_ok=False)

        # test exists_ok = True
        expected = dict(kiwi='taco')
        self.exporter._export_dirs(dirpath, exists_ok=True, metadata=expected)
        result = self.client.folders['baz (1)']['metadata']
        self.assertEqual(result, expected)

    def test_export_asset(self):
        metadata = dict(asset_type='file')
        self.exporter._export_asset(metadata)
        self.assertEqual(self.client.folders, {})
        self.assertEqual(self.client.files, {})

        metadata = dict(
            asset_type='sequence',
            asset_path_relative='foo/bar/baz',
            apple='orange',
        )
        self.exporter._export_asset(metadata)
        result = sorted(list(self.client.folders.keys()))
        self.assertEqual(result, ['bar', 'baz', 'foo'])
        self.assertEqual(self.client.files, {})

    def test_export_content(self):
        expected = dict(
            filepath='/home/ubuntu/foo/bar/taco.txt',
            filepath_relative='foo/bar/taco.txt',
            filename='taco.txt'
        )
        self.exporter._export_content(expected)

        result = list(sorted(self.client.folders.keys()))
        self.assertEqual(result, ['bar', 'foo'])

        result = self.client.items
        self.assertEqual(result['taco.txt']['metadata'], expected)
        self.assertEqual(
            result['taco.txt']['file_content'], expected['filepath']
        )

    def test_export_content_error(self):
        meta = dict(
            filepath='/home/ubuntu/foo/bar/taco.txt',
            filepath_relative='foo/bar/taco.txt',
            filename='taco.txt'
        )
        self.exporter._export_content(meta)

        item = self.client.items['taco.txt']['_id']
        items = self.client.folders['bar']['items']
        self.assertIn(item, items)
