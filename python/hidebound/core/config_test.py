import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest

from schematics.exceptions import ValidationError, DataError

import hidebound.core.config as cfg
# ------------------------------------------------------------------------------


class IsSpecificationFileTests(unittest.TestCase):
    def test_is_specification_file(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'specifications1.py')

            text = '''
                from schematics.types import IntType, ListType, StringType
                from hidebound.core.specification_base import SpecificationBase

                class Spec001(SpecificationBase):
                    foo = ListType(IntType(), required=True)
                    bar = ListType(StringType(), required=True)

                SPECIFICATIONS = [Spec001]'''
            text = re.sub('                ', '', text)
            with open(filepath, 'w') as f:
                f.write(text)
            cfg.is_specification_file(filepath)

    def test_import(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'specifications2.py')

            text = '''
                from schematics.types import IntType, ListType, StringType
                from hidebound.core.specification_base import SpecificationBase

                BIG DUMB ERROR

                class Spec001(SpecificationBase):
                    foo = ListType(IntType(), required=True)
                    bar = ListType(StringType(), required=True)

                SPECIFICATIONS = [Spec001]'''
            text = re.sub('                ', '', text)
            with open(filepath, 'w') as f:
                f.write(text)

            expected = f'{filepath.as_posix()} could not be imported.'
            with self.assertRaisesRegexp(ValidationError, expected):
                cfg.is_specification_file(filepath)

    def test_has_specifications_attribute(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'specifications3.py')

            text = '''
                from schematics.types import IntType, ListType, StringType
                from hidebound.core.specification_base import SpecificationBase

                class Spec001(SpecificationBase):
                    foo = ListType(IntType(), required=True)
                    bar = ListType(StringType(), required=True)'''
            text = re.sub('                ', '', text)
            with open(filepath, 'w') as f:
                f.write(text)

            expected = f'{filepath.as_posix()} has no SPECIFICATIONS attribute.'
            with self.assertRaisesRegexp(ValidationError, expected):
                cfg.is_specification_file(filepath)

    def test_specifications_is_list(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'specifications4.py')

            text = '''
                from schematics.types import IntType, ListType, StringType
                from hidebound.core.specification_base import SpecificationBase

                class Spec001(SpecificationBase):
                    foo = ListType(IntType(), required=True)
                    bar = ListType(StringType(), required=True)

                SPECIFICATIONS = {'spec001': Spec001}'''
            text = re.sub('                ', '', text)
            with open(filepath, 'w') as f:
                f.write(text)

            expected = f'{filepath.as_posix()} SPECIFICATIONS attribute is not '
            expected += 'a list.'
            with self.assertRaisesRegexp(ValidationError, expected):
                cfg.is_specification_file(filepath)

    def test_specificationbase_bad_subclasses(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'specifications5.py')

            text = '''
                from schematics.types import IntType, ListType, StringType
                from hidebound.core.specification_base import SpecificationBase

                class Spec001:
                    foo = ListType(IntType(), required=True)
                    bar = ListType(StringType(), required=True)

                SPECIFICATIONS = [Spec001]'''
            text = re.sub('                ', '', text)
            with open(filepath, 'w') as f:
                f.write(text)

            expected = 'are not subclasses of SpecificationBase.'
            with self.assertRaisesRegexp(ValidationError, expected):
                cfg.is_specification_file(filepath)


class IsHideboundDirectory(unittest.TestCase):
    def test_is_hidebound_directory(self):
        cfg.is_hidebound_directory('/foo/bar/hidebound')

        expected = '/foo/bar directory is not named hidebound.core.'
        with self.assertRaisesRegexp(ValidationError, expected):
            cfg.is_hidebound_directory('/foo/bar')

        expected = '/foo/bar/Hidebound directory is not named hidebound.core.'
        with self.assertRaisesRegexp(ValidationError, expected):
            cfg.is_hidebound_directory('/foo/bar/Hidebound')


# CONFIG------------------------------------------------------------------------
class ConfigTests(unittest.TestCase):
    def write_good_spec(self, temp):
        filepath = Path(temp, 'good_spec.py')

        text = '''
            from schematics.types import IntType, ListType, StringType
            from hidebound.core.specification_base import SpecificationBase

            class Spec001(SpecificationBase):
                foo = ListType(IntType(), required=True)
                bar = ListType(StringType(), required=True)

            SPECIFICATIONS = [Spec001]'''
        text = re.sub('            ', '', text)
        with open(filepath, 'w') as f:
            f.write(text)
        return filepath.as_posix()

    def write_bad_spec(self, temp):
        filepath = Path(temp, 'bad_spec.py')

        text = '''
            from schematics.types import IntType, ListType, StringType
            from hidebound.core.specification_base import SpecificationBase

            class Spec001(SpecificationBase):
                foo = ListType(IntType(), required=True)
                bar = ListType(StringType(), required=True)

            SPECIFICATIONS = ['Foobar']'''
        text = re.sub('            ', '', text)
        with open(filepath, 'w') as f:
            f.write(text)
        return filepath.as_posix()

    def set_data(self, temp):
        self.root = Path(temp, 'root').as_posix()
        self.hb_root = Path(temp, 'hidebound').as_posix()
        self.config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[],
            include_regex='foo',
            exclude_regex='bar',
            write_mode='copy',
        )

    def test_config(self):
        with TemporaryDirectory() as temp:
            self.set_data(temp)
            os.makedirs(self.root)
            os.makedirs(self.hb_root)
            cfg.Config(self.config).validate()

    def test_config_root(self):
        with TemporaryDirectory() as temp:
            self.set_data(temp)
            os.makedirs(self.hb_root)

            expected = 'root_directory.*is not a directory or does not exist'
            with self.assertRaisesRegex(DataError, expected):
                cfg.Config(self.config).validate()

    def test_config_hb_root(self):
        with TemporaryDirectory() as temp:
            self.set_data(temp)
            os.makedirs(self.root)

            expected = 'hidebound_directory.*is not a directory or does '
            expected += 'not exist'
            with self.assertRaisesRegex(DataError, expected):
                cfg.Config(self.config).validate()

    def test_write_mode(self):
        with TemporaryDirectory() as temp:
            self.set_data(temp)
            os.makedirs(self.root)
            os.makedirs(self.hb_root)

            self.config['write_mode'] = 'copy'
            cfg.Config(self.config).validate()

            self.config['write_mode'] = 'move'
            cfg.Config(self.config).validate()

            self.config['write_mode'] = 'shuffle'
            expected = r"shuffle is not in \['copy', 'move'\]"
            with self.assertRaisesRegexp(DataError, expected):
                cfg.Config(self.config).validate()

    def test_specification_files_good(self):
        with TemporaryDirectory() as temp:
            self.set_data(temp)
            os.makedirs(self.root)
            os.makedirs(self.hb_root)

            spec = self.write_good_spec(temp)
            self.config['specification_files'] = [spec]

            cfg.Config(self.config).validate()

    def test_specification_files_bad(self):
        with TemporaryDirectory() as temp:
            self.set_data(temp)
            os.makedirs(self.root)
            os.makedirs(self.hb_root)

            good = self.write_good_spec(temp)
            bad = self.write_bad_spec(temp)
            self.config['specification_files'] = [good, bad]

            expected = 'Foobar.* are not subclasses of SpecificationBase'
            with self.assertRaisesRegexp(DataError, expected):
                cfg.Config(self.config).validate()
