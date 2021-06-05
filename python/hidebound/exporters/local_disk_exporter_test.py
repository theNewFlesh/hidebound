from itertools import chain
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
import os
import re
import unittest

from pandas import DataFrame
from schematics.exceptions import DataError

from hidebound.exporters.local_disk_exporter import LocalDiskConfig, LocalDiskExporter
import hidebound.core.tools as hbt
# ------------------------------------------------------------------------------


class LocalDiskConfigTests(unittest.TestCase):
    def test_validate(self):
        config = dict(target_directory='/foo/bar')
        LocalDiskConfig(config).validate()

    def test_validate_errors(self):
        expected = 'is not a legal directory path'
        for path in ['foo/bar', '\foo\bar', '/foo/bar/', '/foo.bar/baz']:
            with self.assertRaisesRegexp(DataError, expected):
                config = dict(target_directory=path)
                LocalDiskConfig(config).validate()
# ------------------------------------------------------------------------------


class LocalDiskExporterTests(unittest.TestCase):
    def get_config(self, root):
        return dict(target_directory=Path(root, 'target').as_posix())

    def test_from_config(self):
        with TemporaryDirectory() as root:
            config = self.get_config(root)
            result = LocalDiskExporter.from_config(config)
            self.assertIsInstance(result, LocalDiskExporter)

    def test_init(self):
        with TemporaryDirectory() as root:
            config = self.get_config(root)
            result = LocalDiskExporter(**config)
            self.assertIsInstance(result, LocalDiskExporter)
            self.assertTrue(Path(config['target_directory']).is_dir())

    def setup_hidebound_directory(self, root):
        hb_root = Path(root, 'hidebound')
        file_meta = Path(hb_root, 'metadata', 'file')
        asset_meta = Path(hb_root, 'metadata', 'asset')
        content = Path(hb_root, 'content')
        data = []

        # add sequence assets
        proj = 'proj001'
        spec = 'seq001'
        for v in range(0, 2):
            name = f'p-proj001_s-seq001_d-seq_v{v:03d}'
            asset_id = str(uuid4())
            for f in range(0, 3):
                file_id = str(uuid4())
                rel_path = Path(name, name + f'_f{f:04d}.png')
                data.append(dict(
                    project=proj,
                    spec=spec,
                    asset_name=name,
                    asset_id=asset_id,
                    file_id=file_id,
                    a_path=Path(asset_meta, asset_id + '.json').as_posix(),
                    f_path=Path(file_meta, file_id + '.json').as_posix(),
                    c_path=Path(content, proj, spec, rel_path).as_posix()
                ))

        # add file asset
        spec = 'text001'
        filename = f'p-proj001_s-{spec}_d-file_v001.txt'
        asset_id = str(uuid4())
        data.append(dict(
            project=proj,
            spec=spec,
            asset_name=name,
            asset_id=asset_id,
            file_id=None,
            a_path=Path(asset_meta, asset_id + '.json').as_posix(),
            f_path=None,
            c_path=Path(content, proj, spec, filename).as_posix()
        ))
        data = DataFrame(data)

        a_paths = data.a_path.dropna().unique().tolist()
        f_paths = data.f_path.dropna().unique().tolist()
        c_paths = data.c_path.dropna().unique().tolist()
        filepaths = list(chain(a_paths, f_paths, c_paths))
        for filepath in filepaths:
            os.makedirs(Path(filepath).parent, exist_ok=True)
            with open(filepath, 'w') as f:
                f.write('data')

        return hb_root

    def test_export(self):
        with TemporaryDirectory() as root:
            config = self.get_config(root)
            hb_root = self.setup_hidebound_directory(root)
            exp = LocalDiskExporter.from_config(config)

            target = config['target_directory']
            self.assertEqual(len(os.listdir(target)), 0)

            exp.export(hb_root)

            expected = hbt.directory_to_dataframe(hb_root).filepath \
                .apply(lambda x: re.sub('.*/hidebound/', '', x)) \
                .tolist()
            expected = sorted(expected)

            result = hbt.directory_to_dataframe(target).filepath \
                .apply(lambda x: re.sub('.*/target/', '', x)) \
                .tolist()
            result = sorted(result)

            self.assertEqual(result, expected)

            # idempotency
            LocalDiskExporter.from_config(config).export(hb_root)
            result = hbt.directory_to_dataframe(target).filepath \
                .apply(lambda x: re.sub('.*/target/', '', x)) \
                .tolist()
            result = sorted(result)

            self.assertEqual(result, expected)
