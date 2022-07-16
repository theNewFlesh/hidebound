from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
import json
import os
import re
import unittest

from pandas import DataFrame
from schematics.exceptions import DataError
import pytest

from hidebound.exporters.disk_exporter import DiskConfig, DiskExporter
import hidebound.core.tools as hbt
# ------------------------------------------------------------------------------


class DiskConfigTests(unittest.TestCase):
    def test_validate(self):
        config = dict(name='disk', target_directory='/foo/bar')
        DiskConfig(config).validate()

    def test_name(self):
        config = dict(target_directory='/foo/bar')
        with self.assertRaises(DataError):
            DiskConfig(config).validate()

        config = dict(name='foobar', target_directory='/foo/bar')
        with self.assertRaises(DataError):
            DiskConfig(config).validate()

    def test_validate_errors(self):
        expected = 'is not a legal directory path'
        for path in ['foo/bar', '\foo\bar', '/foo/bar/', '/foo.bar/baz']:
            with self.assertRaisesRegexp(DataError, expected):
                config = dict(name='disk', target_directory=path)
                DiskConfig(config).validate()
# ------------------------------------------------------------------------------


class DiskExporterTests(unittest.TestCase):
    def get_config(self, root):
        return dict(target_directory=Path(root, 'target').as_posix())

    def test_from_config(self):
        with TemporaryDirectory() as root:
            config = self.get_config(root)
            result = DiskExporter.from_config(config)
            self.assertIsInstance(result, DiskExporter)

    def test_init(self):
        with TemporaryDirectory() as root:
            config = self.get_config(root)
            result = DiskExporter(**config)
            self.assertIsInstance(result, DiskExporter)
            self.assertTrue(Path(config['target_directory']).is_dir())

    def setup_staging_directory(self, root):
        now = hbt.time_string()

        # create paths
        staging = Path(root, 'hidebound')
        content = Path(staging, 'content')
        meta_root = Path(staging, 'metadata')
        file_meta = Path(meta_root, 'file')
        asset_meta = Path(meta_root, 'asset')
        asset_chunk = Path(
            meta_root, 'asset-chunk', f'hidebound-asset-chunk_{now}.json'
        )
        file_chunk = Path(
            meta_root, 'file-chunk', f'hidebound-file-chunk_{now}.json'
        )

        # add dummy config
        config = Path(staging, 'config')
        os.makedirs(config)
        with open(Path(config, 'hidbound_config.json'), 'w') as f:
            json.dump({'foo': 'bar'}, f)

        data = []

        # add sequence assets
        proj = 'proj001'
        spec = 'seq001'
        for v in range(0, 2):
            name = f'p-proj001_s-seq001_d-seq_v{v:03d}'
            asset_id = str(uuid4())
            for f in range(0, 3):
                file_id = str(uuid4())
                item = Path(name, name + f'_f{f:04d}.png')
                data.append(dict(
                    project=proj,
                    spec=spec,
                    asset_name=name,
                    asset_id=asset_id,
                    file_id=file_id,
                    asset_meta_path=Path(asset_meta, asset_id + '.json').as_posix(),
                    file_meta_path=Path(file_meta, file_id + '.json').as_posix(),
                    asset_path=Path(content, proj, spec, name).as_posix(),
                    asset_path_relative=Path(proj, spec, name).as_posix(),
                    filepath=Path(content, proj, spec, item).as_posix(),
                    filepath_relative=Path(proj, spec, item).as_posix(),
                ))

        # add file asset
        spec = 'text001'
        name = f'p-proj001_s-{spec}_d-file_v001.txt'
        asset_id = str(uuid4())
        file_id = str(uuid4())
        data.append(dict(
            project=proj,
            spec=spec,
            asset_name=name,
            asset_id=asset_id,
            file_id=file_id,
            asset_meta_path=Path(asset_meta, asset_id + '.json').as_posix(),
            file_meta_path=Path(file_meta, file_id + '.json').as_posix(),
            asset_path=Path(content, proj, spec, name).as_posix(),
            asset_path_relative=Path(proj, spec, name).as_posix(),
            filepath=Path(content, proj, spec, name).as_posix(),
            filepath_relative=Path(proj, spec, name).as_posix(),
        ))
        data = DataFrame(data)

        # make directories
        for col in ['asset_meta_path', 'file_meta_path', 'filepath']:
            data[col].dropna().apply(
                lambda x: os.makedirs(Path(x).parent, exist_ok=True)
            )
        os.makedirs(asset_chunk.parent, exist_ok=True)
        os.makedirs(file_chunk.parent, exist_ok=True)

        # write asset metadata
        assets = data \
            .groupby('asset_id') \
            .apply(lambda x: dict(
                asset_id=x.asset_id.tolist()[0],
                file_ids=x.file_id.tolist(),
                asset_meta_path=x.asset_meta_path.tolist()[0],
                asset_name=x.asset_name.tolist()[0],
                asset_path=x.asset_path.tolist()[0],
                asset_path_relative=x.asset_path_relative.tolist()[0],
                filepaths=x.filepath.tolist(),
                filepath_relatives=x.filepath_relative.tolist(),
            ))
        assets.apply(lambda x: hbt.write_json(x, x['asset_meta_path']))

        # write asset chunk
        hbt.write_json(assets.tolist(), asset_chunk)

        # write file metadata
        data.apply(
            lambda x: hbt.write_json(x.to_dict(), x['file_meta_path']),
            axis=1,
        )

        # write file chunk
        meta = data.apply(lambda x: x.to_dict(), axis=1).tolist()
        hbt.write_json(meta, file_chunk)

        # write content
        data.apply(lambda x: hbt.write_json({}, x['filepath']), axis=1)

        return staging

    @pytest.mark.flakey
    def test_export(self):
        with TemporaryDirectory() as root:
            config = self.get_config(root)
            staging = self.setup_staging_directory(root)
            exp = DiskExporter.from_config(config)

            target = config['target_directory']
            self.assertEqual(len(os.listdir(target)), 0)

            exp.export(staging)

            expected = hbt.directory_to_dataframe(staging)
            mask = expected.filepath \
                .apply(lambda x: re.search('/(content|metadata)', x)) \
                .astype(bool)
            expected = expected[mask]
            expected = expected.filepath \
                .apply(lambda x: re.sub('.*/hidebound/', '', x)) \
                .tolist()
            expected = sorted(expected)

            result = hbt.directory_to_dataframe(target).filepath \
                .apply(lambda x: re.sub('.*/target/', '', x)) \
                .tolist()
            result = sorted(result)

            self.assertEqual(result, expected)

            # idempotency
            DiskExporter.from_config(config).export(staging)
            result = hbt.directory_to_dataframe(target).filepath \
                .apply(lambda x: re.sub('.*/target/', '', x)) \
                .tolist()
            result = sorted(result)

            self.assertEqual(result, expected)

    def test_export_content(self):
        with TemporaryDirectory() as root:
            config = self.get_config(root)
            exp = DiskExporter.from_config(config)

            src = Path(root, 'source', 'content.json')
            src_rel = Path('content.json')
            os.makedirs(src.parent)
            hbt.write_json({'foo': 'bar'}, src)

            meta = dict(
                filepath=src.as_posix(),
                filepath_relative=src_rel.as_posix(),
            )
            exp._export_content(meta)

            target = Path(exp._target_directory, 'content', 'content.json')
            self.assertTrue(target.is_file())

            result = hbt.read_json(target)
            expected = hbt.read_json(src)
            self.assertEqual(result, expected)

    def test_export_asset(self):
        with TemporaryDirectory() as root:
            config = self.get_config(root)
            exp = DiskExporter.from_config(config)

            result = Path(
                exp._target_directory, 'metadata', 'asset', '1234.json'
            )
            expected = dict(asset_id='1234')
            os.makedirs(result.parent)
            exp._export_asset(expected)

            self.assertTrue(result.is_file())
            result = hbt.read_json(result)
            self.assertEqual(result, expected)

    def test_export_file(self):
        with TemporaryDirectory() as root:
            config = self.get_config(root)
            exp = DiskExporter.from_config(config)

            result = Path(
                exp._target_directory, 'metadata', 'file', '1234.json'
            )
            expected = dict(file_id='1234')
            os.makedirs(result.parent)
            exp._export_file(expected)

            self.assertTrue(result.is_file())
            result = hbt.read_json(result)
            self.assertEqual(result, expected)

    def test_export_asset_chunk(self):
        with TemporaryDirectory() as root:
            config = self.get_config(root)
            exp = DiskExporter.from_config(config)

            result = Path(exp._target_directory, 'metadata', 'asset-chunk')
            os.makedirs(result.parent)
            expected = [dict(foo='bar')]
            exp._export_asset_chunk(expected)

            result = Path(result, os.listdir(result)[0])
            self.assertTrue(result.is_file())
            result = hbt.read_json(result)
            self.assertEqual(result, expected)

    def test_export_file_chunk(self):
        with TemporaryDirectory() as root:
            config = self.get_config(root)
            exp = DiskExporter.from_config(config)

            result = Path(exp._target_directory, 'metadata', 'file-chunk')
            os.makedirs(result.parent)
            expected = [dict(foo='bar')]
            exp._export_file_chunk(expected)

            result = Path(result, os.listdir(result)[0])
            self.assertTrue(result.is_file())
            result = hbt.read_json(result)
            self.assertEqual(result, expected)
