import json
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import shutil
import unittest

from hidebound.exporters.exporter_base import ExporterBase
# ------------------------------------------------------------------------------


class ExporterBaseTests(unittest.TestCase):
    def create_data(self, root):
        data = Path(root, 'content')
        metadata = Path(root, 'metadata')
        asset = Path(root, 'metadata', 'asset')
        file_ = Path(root, 'metadata', 'file')
        asset_chunk_path = Path(root, 'metadata', 'asset-chunk')
        file_chunk_path = Path(root, 'metadata', 'file-chunk')
        logs = Path(root, 'logs')

        os.makedirs(data)
        os.makedirs(metadata)
        os.makedirs(asset)
        os.makedirs(file_)
        os.makedirs(asset_chunk_path)
        os.makedirs(file_chunk_path)
        os.makedirs(logs)
        asset_chunk_name = 'hidebound-asset-chunk_01-01-01T01-01-01.json'
        asset_chunk_path = Path(asset_chunk_path, asset_chunk_name)
        file_chunk_name = 'hidebound-file-chunk_01-01-01T01-01-01.json'
        file_chunk_path = Path(file_chunk_path, file_chunk_name)

        # create asset data
        assets = [
            [Path(asset, '1.json'), dict(file_ids=['1-1', '1-2', '1-3'])],
            [Path(asset, '2.json'), dict(file_ids=['2-1', '2-2', '2-3'])],
            [Path(asset, '3.json'), dict(file_ids=['3-1', '3-2', '3-3'])],
        ]

        # create file data
        files = [
            [Path(file_, '1-1.json'), dict(foo='bar-1-1')],
            [Path(file_, '1-2.json'), dict(foo='bar-1-2')],
            [Path(file_, '1-3.json'), dict(foo='bar-1-3')],
            [Path(file_, '2-1.json'), dict(foo='bar-2-1')],
            [Path(file_, '2-2.json'), dict(foo='bar-2-2')],
            [Path(file_, '2-3.json'), dict(foo='bar-2-3')],
            [Path(file_, '3-1.json'), dict(foo='bar-3-1')],
            [Path(file_, '3-2.json'), dict(foo='bar-3-2')],
            [Path(file_, '3-3.json'), dict(foo='bar-3-3')],
        ]

        # write asset metadata
        for filepath, data in assets:
            with open(filepath, 'w') as f:
                json.dump(data, f)

        # write asset chunk
        asset_chunk = [x[1] for x in assets]
        with open(asset_chunk_path, 'w') as f:
            json.dump(asset_chunk, f)

        # write file metadata
        for filepath, data in files:
            with open(filepath, 'w') as f:
                json.dump(data, f)

        # write file chunk
        file_chunk = [x[1] for x in files]
        with open(file_chunk_path, 'w') as f:
            json.dump(file_chunk, f)

        return assets, files, asset_chunk, file_chunk

    def test_enforce_directory_structure(self):
        with TemporaryDirectory() as root:
            content = Path(root, 'content')
            metadata = Path(root, 'metadata')
            asset = Path(root, 'metadata', 'asset')
            file_ = Path(root, 'metadata', 'file')
            asset_chunk = Path(root, 'metadata', 'asset-chunk')
            file_chunk = Path(root, 'metadata', 'file-chunk')
            logs = Path(root, 'logs')

            dirs = [
                content, metadata, asset, file_, asset_chunk, file_chunk, logs
            ]
            for dir_ in dirs:
                os.makedirs(dir_)
            ExporterBase()._enforce_directory_structure(root)

            for dir_ in dirs:
                for dir_ in dirs:
                    os.makedirs(dir_, exist_ok=True)
                shutil.rmtree(dir_)
                expected = f'{dir_.as_posix()} directory does not exist.'
                with self.assertRaisesRegexp(FileNotFoundError, expected):
                    ExporterBase()._enforce_directory_structure(root)
                os.makedirs(dir_)

    def test_export(self):
        r_assets = []
        r_files = []
        r_asset_chunk = []
        r_file_chunk = []

        class Foo(ExporterBase):
            def _export_asset(self, metadata):
                r_assets.append(metadata)

            def _export_file(self, metadata):
                r_files.append(metadata)

            def _export_asset_chunk(self, metadata):
                r_asset_chunk.append(metadata)

            def _export_file_chunk(self, metadata):
                r_file_chunk.append(metadata)

        with TemporaryDirectory() as root:
            e_assets, e_files, e_asset_chunk, e_file_chunk = self.create_data(root)
            e_assets = [x[1] for x in e_assets]
            e_files = [x[1] for x in e_files]

            Foo().export(root)

            # asset
            self.assertEqual(r_assets, e_assets)

            # file
            self.assertEqual(r_files, e_files)

            # asset-chunk
            r_asset_chunk = r_asset_chunk[0]
            self.assertEqual(len(r_asset_chunk), len(e_asset_chunk))
            for expected in e_asset_chunk:
                self.assertIn(expected, r_asset_chunk)

            # file-chunk
            r_file_chunk = r_file_chunk[0]
            self.assertEqual(len(r_file_chunk), len(e_file_chunk))
            for expected in e_file_chunk:
                self.assertIn(expected, r_file_chunk)

    def test_export_asset(self):
        class Foo(ExporterBase):
            pass
        expected = '_export_asset method must be implemented in subclass.'
        with self.assertRaisesRegexp(NotImplementedError, expected):
            Foo()._export_asset({})

    def test_export_file(self):
        class Foo(ExporterBase):
            pass
        expected = '_export_file method must be implemented in subclass.'
        with self.assertRaisesRegexp(NotImplementedError, expected):
            Foo()._export_file({})

    def test_export_asset_chunk(self):
        class Foo(ExporterBase):
            pass
        expected = '_export_asset_chunk method must be implemented in subclass.'
        with self.assertRaisesRegexp(NotImplementedError, expected):
            Foo()._export_asset_chunk({})

    def test_export_file_chunk(self):
        class Foo(ExporterBase):
            pass
        expected = '_export_file_chunk method must be implemented in subclass.'
        with self.assertRaisesRegexp(NotImplementedError, expected):
            Foo()._export_file_chunk({})
