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

        os.makedirs(data)
        os.makedirs(metadata)
        os.makedirs(asset)
        os.makedirs(file_)

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

        for filepath, data in assets:
            with open(filepath, 'w') as f:
                json.dump(data, f)

        for filepath, data in files:
            with open(filepath, 'w') as f:
                json.dump(data, f)

        return assets, files

    def test_enforce_directory_structure(self):
        with TemporaryDirectory() as root:
            data = Path(root, 'content')
            metadata = Path(root, 'metadata')
            asset = Path(root, 'metadata', 'asset')
            file_ = Path(root, 'metadata', 'file')

            os.makedirs(data)
            os.makedirs(metadata)
            os.makedirs(asset)
            os.makedirs(file_)
            ExporterBase()._enforce_directory_structure(root)

            dirs = [data, asset, file_, metadata]
            for dir_ in dirs:
                shutil.rmtree(dir_)
                expected = f'{dir_.as_posix()} directory does not exist.'
                with self.assertRaisesRegexp(FileNotFoundError, expected):
                    ExporterBase()._enforce_directory_structure(root)
                os.makedirs(dir_)

    def test_export(self):
        r_assets = []
        r_files = []

        class Foo(ExporterBase):
            def _export_asset(self, metadata):
                r_assets.append(metadata)

            def _export_file(self, metadata):
                r_files.append(metadata)

        with TemporaryDirectory() as root:
            e_assets, e_files = self.create_data(root)
            e_assets = [x[1] for x in e_assets]
            e_files = [x[1] for x in e_files]

            Foo().export(root)
            self.assertEqual(r_assets, e_assets)
            self.assertEqual(r_files, e_files)

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
