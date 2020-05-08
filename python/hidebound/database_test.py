import json
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import re

from schematics.exceptions import DataError

from hidebound.database import Database
from hidebound.database_test_base import DatabaseTestBase
import hidebound.tools as tools
# ------------------------------------------------------------------------------


class DatabaseTests(DatabaseTestBase):
    def write_spec_file(self, root):
        os.makedirs(Path(root, 'specs'))
        spec_file = Path(root, 'specs', 'specs.py').as_posix()

        text = '''
            from schematics.types import IntType, ListType, StringType
            from hidebound.specification_base import SpecificationBase

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
            hb_root = Path(root, 'hb_root').as_posix()
            os.makedirs(hb_root)
            spec_file = self.write_spec_file(root)

            config = dict(
                root_directory=root,
                hidebound_parent_directory=hb_root,
                specification_files=[spec_file],
                include_regex='foo',
                exclude_regex='bar',
                write_mode='copy',
            )
            Database.from_config(config)

            config['specification_files'] = ['/foo/bar.py']
            with self.assertRaises(DataError):
                Database.from_config(config)

    def test_from_json(self):
        with TemporaryDirectory() as root:
            # create hb root dir
            hb_root = Path(root, 'hb_root').as_posix()
            os.makedirs(hb_root)
            spec_file = self.write_spec_file(root)

            config = dict(
                root_directory=root,
                hidebound_parent_directory=hb_root,
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
            hb_root = Path(root, 'hb_root')
            os.makedirs(hb_root)

            self.create_files(root)
            Database(root, hb_root)
            Database(root, hb_root, [Spec001])
            Database(root, hb_root, [Spec001, Spec002])

            expected = Path(hb_root, 'hidebound')
            self.assertTrue(os.path.exists(expected))

    def test_init_bad_root(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        expected = '/foo is not a directory or does not exist.'
        with self.assertRaisesRegexp(FileNotFoundError, expected):
            Database('/foo', '/bar', [Spec001])

    def test_init_bad_hb_root(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hb_root')
            expected = '/hb_root is not a directory or does not exist'
            with self.assertRaisesRegexp(FileNotFoundError, expected):
                Database(root, hb_root)

    def test_init_bad_specifications(self):
        Spec001, Spec002, BadSpec = self.get_specifications()
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hb_root')
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
            hb_root = Path(root, 'hb_root')
            os.makedirs(hb_root)

            expected = r"Invalid write mode: foo not in \['copy', 'move'\]\."
            with self.assertRaisesRegexp(ValueError, expected):
                Database(root, hb_root, [Spec001], write_mode='foo')

    # UPDATE--------------------------------------------------------------------
    def test_update(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hb_root')
            os.makedirs(hb_root)
            Spec001, Spec002, BadSpec = self.get_specifications()

            expected = self.create_files(root).filepath\
                .apply(lambda x: x.as_posix()).tolist()
            expected = sorted(expected)

            data = Database(root, hb_root, [Spec001, Spec002]).update().data
            result = data.filepath.tolist()
            result = sorted(result)
            self.assertEqual(result, expected)

            result = data.groupby('asset_path').asset_valid.first().tolist()
            expected = [True, True, False, True, False]
            self.assertEqual(result, expected)

    def test_update_exclude(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hb_root')
            os.makedirs(hb_root)
            Spec001, Spec002, BadSpec = self.get_specifications()

            expected = self.create_files(root).filepath\
                .apply(lambda x: x.as_posix()).tolist()
            regex = r'misc\.txt|vdb'
            expected = list(filter(lambda x: not re.search(regex, x), expected))
            expected = sorted(expected)

            result = Database(root, hb_root, [Spec001, Spec002], exclude_regex=regex)\
                .update().data.filepath.tolist()
            result = sorted(result)
            self.assertEqual(result, expected)

    def test_update_include(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hb_root')
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
            hb_root = Path(root, 'hb_root')
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
            hb_root = Path(root, 'hb_root')
            os.makedirs(hb_root)
            result = Database(root, hb_root, [Spec001]).update().data
            self.assertEqual(len(result), 0)
            self.assertEqual(result.columns.tolist(), self.columns)

    def test_update_error(self):
        Spec001, Spec002, BadSpec = self.get_specifications()

        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hb_root')
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

    # CREATE--------------------------------------------------------------------
    def test_create(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hb_root')
            os.makedirs(hb_root)
            Spec001, Spec002, BadSpec = self.get_specifications()
            self.create_files(root)

            db = Database(root, hb_root, [Spec001, Spec002])
            db.update()
            data = db.data
            db.create()

            data = data[data.asset_valid]

            # ensure files are written
            result = Path(hb_root, 'hidebound/data')
            result = tools.directory_to_dataframe(result)
            result = sorted(result.filename.tolist())
            self.assertGreater(len(result), 0)
            expected = sorted(data.filename.tolist())
            self.assertEqual(result, expected)

            # ensure file metadata is written
            result = len(os.listdir(Path(hb_root, 'hidebound/metadata/file')))
            self.assertGreater(result, 0)
            expected = data.filepath.nunique()
            self.assertEqual(result, expected)

            # ensure asset metadata is written
            result = len(os.listdir(Path(hb_root, 'hidebound/metadata/asset')))
            self.assertGreater(result, 0)
            expected = data.asset_path.nunique()
            self.assertEqual(result, expected)

    def test_create_all_invalid(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hb_root')
            os.makedirs(hb_root)
            Spec001, Spec002, BadSpec = self.get_specifications()
            self.create_files(root)

            db = Database(root, hb_root, [Spec001, Spec002])
            db.update()
            data = db.data
            data['asset_valid'] = False
            db.create()

            result = Path(hb_root, 'hidebound/data')
            self.assertFalse(result.exists())

            result = Path(hb_root, 'hidebound/metadata/file')
            self.assertFalse(result.exists())

            result = Path(hb_root, 'hidebound/metadata/asset')
            self.assertFalse(result.exists())

    def test_create_copy(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hb_root')
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

            result = tools.directory_to_dataframe(root).filepath.tolist()
            result = sorted(result)
            self.assertEqual(result, expected)

    def test_create_move(self):
        with TemporaryDirectory() as root:
            hb_root = Path(root, 'hb_root')
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
            result = Path(hb_root, 'hidebound/data')
            result = tools.directory_to_dataframe(result)
            result = sorted(result.filename.tolist())
            self.assertGreater(len(result), 0)
            expected = sorted(data.filename.tolist())
            self.assertEqual(result, expected)

            # ensure file metadata is written
            result = len(os.listdir(Path(hb_root, 'hidebound/metadata/file')))
            self.assertGreater(result, 0)
            expected = data.filepath.nunique()
            self.assertEqual(result, expected)

            # ensure asset metadata is written
            result = len(os.listdir(Path(hb_root, 'hidebound/metadata/asset')))
            self.assertGreater(result, 0)
            expected = data.asset_path.nunique()
            self.assertEqual(result, expected)
