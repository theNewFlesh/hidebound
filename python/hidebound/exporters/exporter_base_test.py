from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import shutil
import unittest

from schematics.exceptions import DataError

from hidebound.exporters.exporter_base import ExporterBase, ExporterConfigBase
import hidebound.core.tools as hbt
# ------------------------------------------------------------------------------


class Foo(ExporterBase):
    def __init__(
        self, metadata_types=['asset', 'file', 'asset-chunk', 'file-chunk']
    ):
        super().__init__(metadata_types=metadata_types)
        self.content = []
        self.assets = []
        self.files = []
        self.asset_chunk = None
        self.file_chunk = None

    def _export_content(self, metadata):
        self.content.append(metadata)

    def _export_asset(self, metadata):
        self.assets.append(metadata)

    def _export_file(self, metadata):
        self.files.append(metadata)

    def _export_asset_chunk(self, metadata):
        self.asset_chunk = metadata

    def _export_file_chunk(self, metadata):
        self.file_chunk = metadata


class ExporterConfigBaseTests(unittest.TestCase):
    def test_metadata_types(self):
        config = dict(
            metadata_types=['asset', 'file', 'asset-chunk', 'file-chunk']
        )
        ExporterConfigBase(config).validate()

        for mtype in ['asset', 'file', 'asset-chunk', 'file-chunk']:
            config = dict(metadata_types=[mtype])
            ExporterConfigBase(config).validate()

        config = dict(metadata_types=[])
        ExporterConfigBase(config).validate()

        ExporterConfigBase({}).validate()

        config = dict(metadata_types=['foobar', 'file-chunk', 'x'])
        expected = 'foobar is not a legal metadata type.'
        with self.assertRaisesRegex(DataError, expected):
            ExporterConfigBase(config).validate()


class ExporterBaseTests(unittest.TestCase):
    def create_data(self, root):
        data = Path(root, 'content')
        metadata = Path(root, 'metadata')
        asset = Path(root, 'metadata', 'asset')
        file_ = Path(root, 'metadata', 'file')
        asset_chunk_path = Path(root, 'metadata', 'asset-chunk')
        file_chunk_path = Path(root, 'metadata', 'file-chunk')

        os.makedirs(data)
        os.makedirs(metadata)
        os.makedirs(asset)
        os.makedirs(file_)
        os.makedirs(asset_chunk_path)
        os.makedirs(file_chunk_path)
        asset_chunk_name = 'hidebound-asset-chunk_01-01-01T01-01-01.json'
        asset_chunk_path = Path(asset_chunk_path, asset_chunk_name)
        file_chunk_name = 'hidebound-file-chunk_01-01-01T01-01-01.json'
        file_chunk_path = Path(file_chunk_path, file_chunk_name)

        # create asset data
        assets = [
            dict(
                asset_path=Path(asset, '1.json').as_posix(),
                file_ids=['1-1', '1-2', '1-3'],
            ),
            dict(
                asset_path=Path(asset, '2.json').as_posix(),
                file_ids=['2-1', '2-2', '2-3'],
            ),
            dict(
                asset_path=Path(asset, '3.json').as_posix(),
                file_ids=['3-1', '3-2', '3-3'],
            ),
        ]

        # create file data
        files = [
            dict(filepath=Path(file_, '1-1.json').as_posix(), foo='bar-1-1'),
            dict(filepath=Path(file_, '1-2.json').as_posix(), foo='bar-1-2'),
            dict(filepath=Path(file_, '1-3.json').as_posix(), foo='bar-1-3'),
            dict(filepath=Path(file_, '2-1.json').as_posix(), foo='bar-2-1'),
            dict(filepath=Path(file_, '2-2.json').as_posix(), foo='bar-2-2'),
            dict(filepath=Path(file_, '2-3.json').as_posix(), foo='bar-2-3'),
            dict(filepath=Path(file_, '3-1.json').as_posix(), foo='bar-3-1'),
            dict(filepath=Path(file_, '3-2.json').as_posix(), foo='bar-3-2'),
            dict(filepath=Path(file_, '3-3.json').as_posix(), foo='bar-3-3'),
        ]

        # write asset metadata
        for data in assets:
            hbt.write_json(data, data['asset_path'])

        # write asset chunk
        hbt.write_json(assets, asset_chunk_path)

        # write file metadata
        for data in files:
            hbt.write_json(data, data['filepath'])

        # write file chunk
        hbt.write_json(files, file_chunk_path)

        return files, assets, files

    def test_init(self):
        result = Foo(metadata_types=['file'])
        self.assertEqual(result._metadata_types, ['file'])

        result = datetime.strptime(result._time, '%Y-%m-%dT-%H-%M-%S')
        expected = datetime.now()
        self.assertGreaterEqual(expected, result)

    def test_enforce_directory_structure(self):
        with TemporaryDirectory() as root:
            content = Path(root, 'content')
            metadata = Path(root, 'metadata')
            asset = Path(root, 'metadata', 'asset')
            file_ = Path(root, 'metadata', 'file')
            asset_chunk = Path(root, 'metadata', 'asset-chunk')
            file_chunk = Path(root, 'metadata', 'file-chunk')

            dirs = [content, metadata, asset, file_, asset_chunk, file_chunk]
            for dir_ in dirs:
                os.makedirs(dir_)
            ExporterBase()._enforce_directory_structure(root)

            for dir_ in dirs:
                for dir_ in dirs:
                    os.makedirs(dir_, exist_ok=True)
                shutil.rmtree(dir_)
                expected = f'{dir_.as_posix()} directory does not exist.'
                with self.assertRaisesRegex(FileNotFoundError, expected):
                    ExporterBase()._enforce_directory_structure(root)
                os.makedirs(dir_)

    def test_export(self):
        with TemporaryDirectory() as root:
            e_content, e_assets, e_files = self.create_data(root)
            foo = Foo()
            foo.export(root)

            # content
            self.assertEqual(foo.content, e_content)

            # asset
            self.assertEqual(foo.assets, e_assets)

            # file
            self.assertEqual(foo.files, e_files)

            # asset-chunk
            self.assertEqual(len(foo.asset_chunk), len(e_assets))
            for expected in e_assets:
                self.assertIn(expected, foo.asset_chunk)

            # file-chunk
            self.assertEqual(len(foo.file_chunk), len(e_files))
            for expected in e_files:
                self.assertIn(expected, foo.file_chunk)

    def test_metadata_types(self):
        with TemporaryDirectory() as root:
            e_content, e_assets, e_files = self.create_data(root)
            foo = Foo(metadata_types=['asset', 'file-chunk'])
            foo.export(root)

            # content
            self.assertEqual(foo.content, e_content)

            # asset
            self.assertEqual(foo.assets, e_assets)

            # file
            self.assertEqual(foo.files, [])

            # asset-chunk
            self.assertIsNone(foo.asset_chunk)

            # file-chunk
            self.assertEqual(len(foo.file_chunk), len(e_files))
            for expected in e_files:
                self.assertIn(expected, foo.file_chunk)

    def test_export_content(self):
        class Bar(ExporterBase):
            pass
        expected = '_export_content method must be implemented in subclass.'
        with self.assertRaisesRegex(NotImplementedError, expected):
            Bar()._export_content({})

    def test_export_asset(self):
        class Bar(ExporterBase):
            pass
        expected = '_export_asset method must be implemented in subclass.'
        with self.assertRaisesRegex(NotImplementedError, expected):
            Bar()._export_asset({})

    def test_export_file(self):
        class Bar(ExporterBase):
            pass
        expected = '_export_file method must be implemented in subclass.'
        with self.assertRaisesRegex(NotImplementedError, expected):
            Bar()._export_file({})

    def test_export_asset_chunk(self):
        class Bar(ExporterBase):
            pass
        expected = '_export_asset_chunk method must be implemented in subclass.'
        with self.assertRaisesRegex(NotImplementedError, expected):
            Bar()._export_asset_chunk({})

    def test_export_file_chunk(self):
        class Bar(ExporterBase):
            pass
        expected = '_export_file_chunk method must be implemented in subclass.'
        with self.assertRaisesRegex(NotImplementedError, expected):
            Bar()._export_file_chunk({})
