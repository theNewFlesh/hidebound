import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from girder_client import HttpError
from schematics.exceptions import DataError

from hidebound.exporters.girder_exporter import GirderConfig, GirderExporter
from hidebound.exporters.mock_girder import MockGirderClient
# ------------------------------------------------------------------------------


class GirderConfigTests(unittest.TestCase):
    def setUp(self):
        self.config = dict(
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

    def test_root_type(self):
        config = self.config
        expected = r"foo is not in \[\'collection\', \'folder\'\]"
        config['root_type'] = 'foo'
        with self.assertRaisesRegexp(DataError, expected):
            GirderConfig(config).validate()

    def test_host(self):
        config = self.config
        expected = 'Not a well-formed URL'
        config['host'] = '0.1.2'
        with self.assertRaisesRegexp(DataError, expected):
            GirderConfig(config).validate()

        config['host'] = 'foo.bar.com'
        with self.assertRaisesRegexp(DataError, expected):
            GirderConfig(config).validate()

        config = self.config
        del config['host']
        result = GirderConfig(config).to_primitive()['host']
        self.assertEqual(result, 'http://0.0.0.0')

    def test_port(self):
        config = self.config
        expected = '1023 !> 1023.'
        config['port'] = 1023
        with self.assertRaisesRegexp(DataError, expected):
            GirderConfig(config).validate()

        expected = '65536 !< 65536.'
        config['port'] = 65536
        with self.assertRaisesRegexp(DataError, expected):
            GirderConfig(config).validate()
# ------------------------------------------------------------------------------


class GirderExporterTests(unittest.TestCase):
    def setUp(self):
        self.client = MockGirderClient()
        self.config = dict(
            api_key='api_key',
            root_id='root_id',
            root_type='collection',
            host='http://2.2.2.2',
            port=5555,
        )
        self.exporter = GirderExporter(**self.config, client=self.client)

    def create_data(self, root):
        data = Path(root, 'content')
        metadata = Path(root, 'metadata')
        asset = Path(root, 'metadata', 'asset')
        file_ = Path(root, 'metadata', 'file')

        os.makedirs(data)
        os.makedirs(metadata)
        os.makedirs(asset)
        os.makedirs(file_)

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

        return assets, files

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

    def test_export(self):
        with TemporaryDirectory() as root:
            self.client = MockGirderClient(add_suffix=False)

            e_assets, e_files = self.create_data(root)
            e_assets = [x[1]['asset_name'] for x in e_assets]
            e_files = [x[1]['filename'] for x in e_files]

            # import subprocess
            # x = subprocess.Popen(
            #     f'tree {root}', stdout=subprocess.PIPE, shell=True
            # )
            # x.wait()
            # print(x.stdout.read().decode('utf-8'))

            exporter = GirderExporter\
                .from_config(self.config, client=self.client)
            exporter.export(root)

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

        expected = 'foo/bar/baz directory already exists'
        with self.assertRaisesRegexp(HttpError, expected):
            self.exporter._export_asset(metadata)

    def test_export_file(self):
        expected = dict(
            filepath='/home/ubuntu/foo/bar/taco.txt',
            filepath_relative='foo/bar/taco.txt',
            filename='taco.txt'
        )
        self.exporter._export_file(expected)

        result = list(sorted(self.client.folders.keys()))
        self.assertEqual(result, ['bar', 'foo'])

        result = self.client.items
        self.assertEqual(result['taco.txt']['metadata'], expected)
        self.assertEqual(
            result['taco.txt']['file_content'], expected['filepath']
        )

    def test_export_file_error(self):
        meta = dict(
            filepath='/home/ubuntu/foo/bar/taco.txt',
            filepath_relative='foo/bar/taco.txt',
            filename='taco.txt'
        )
        self.exporter._export_file(meta)

        item = self.client.items['taco.txt']['_id']
        items = self.client.folders['bar']['items']
        self.assertIn(item, items)
