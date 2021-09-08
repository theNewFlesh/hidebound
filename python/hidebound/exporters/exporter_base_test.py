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
        asset_log_path = Path(root, 'logs', 'asset')
        file_log_path = Path(root, 'logs', 'file')

        os.makedirs(data)
        os.makedirs(metadata)
        os.makedirs(asset)
        os.makedirs(file_)
        os.makedirs(asset_log_path)
        os.makedirs(file_log_path)
        asset_log_name = 'hidebound-asset-log_01-01-01T01-01-01.json'
        asset_log_path = Path(asset_log_path, asset_log_name)
        file_log_name = 'hidebound-file-log_01-01-01T01-01-01.json'
        file_log_path = Path(file_log_path, file_log_name)

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
        asset_log = []
        for filepath, data in assets:
            asset_log.append(json.dumps(data))
            with open(filepath, 'w') as f:
                json.dump(data, f)

        # write asset log
        asset_log = '[\n' + '\n'.join(asset_log) + ']'
        with open(asset_log_path, 'w') as f:
            f.write(asset_log)

        # write file metadata
        file_log = []
        for filepath, data in files:
            file_log.append(json.dumps(data))
            with open(filepath, 'w') as f:
                json.dump(data, f)

        # write file log
        file_log = '[\n' + '\n'.join(file_log) + ']'
        with open(file_log_path, 'w') as f:
            f.write(file_log)

        asset_log = dict(filename=asset_log_name, content=asset_log)
        file_log = dict(filename=file_log_name, content=file_log)

        return assets, files, asset_log, file_log

    def test_enforce_directory_structure(self):
        with TemporaryDirectory() as root:
            content = Path(root, 'content')
            metadata = Path(root, 'metadata')
            asset = Path(root, 'metadata', 'asset')
            file_ = Path(root, 'metadata', 'file')
            logs = Path(root, 'logs')
            asset_log = Path(logs, 'asset')
            file_log = Path(logs, 'file')

            dirs = [content, metadata, asset, file_, logs, asset_log, file_log]
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
        r_asset_log = []
        r_file_log = []

        class Foo(ExporterBase):
            def _export_asset(self, metadata):
                r_assets.append(metadata)

            def _export_file(self, metadata):
                r_files.append(metadata)

            def _export_asset_log(self, metadata):
                r_asset_log.append(metadata)

            def _export_file_log(self, metadata):
                r_file_log.append(metadata)

        with TemporaryDirectory() as root:
            e_assets, e_files, e_asset_log, e_file_log = self.create_data(root)
            e_assets = [x[1] for x in e_assets]
            e_files = [x[1] for x in e_files]

            Foo().export(root)
            self.assertEqual(r_assets, e_assets)
            self.assertEqual(r_files, e_files)
            self.assertEqual(r_asset_log[0], e_asset_log)
            self.assertEqual(r_file_log[0], e_file_log)

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

    def test_export_asset_log(self):
        class Foo(ExporterBase):
            pass
        expected = '_export_asset_log method must be implemented in subclass.'
        with self.assertRaisesRegexp(NotImplementedError, expected):
            Foo()._export_asset_log({})

    def test_export_file_log(self):
        class Foo(ExporterBase):
            pass
        expected = '_export_file_log method must be implemented in subclass.'
        with self.assertRaisesRegexp(NotImplementedError, expected):
            Foo()._export_file_log({})
