from pathlib import Path
import os
from tempfile import TemporaryDirectory
import time
import unittest

from pandas import DataFrame

from nerve.database import Database
from nerve.specification_base import Specification
# ------------------------------------------------------------------------------


class DatabaseTests(unittest.TestCase):
    def create_files(self, root):
        fullpaths = [
            'a/1.foo',
            'a/b/2.json',
            'a/b/3.txt',
            'a/b/c/4.json',
            'a/b/c/5.txt'
        ]
        fullpaths = [Path(root, x) for x in fullpaths]
        for fullpath in fullpaths:
            os.makedirs(fullpath.parent, exist_ok=True)
            with open(fullpath, 'w') as f:
                f.write('')
        return fullpaths

    def get_specifications(self):
        class Spec001(Specification):
            pass

        class Spec002(Specification):
            pass

        class BadSpec:
            pass

        return Spec001, Spec002, BadSpec

    def test_init(self):
        Spec001, Spec002, BadSpec = self.get_specifications()

        expected = '/foo is not a directory or does not exist.'
        with self.assertRaisesRegexp(FileNotFoundError, expected):
            Database('/foo', [Spec001])

        with TemporaryDirectory() as root:
            self.create_files(root)
            expected = 'Specification may only contain subclasses of Specification. Found: .*.'

            with self.assertRaisesRegexp(TypeError, expected):
                Database(root, [BadSpec])

            with self.assertRaisesRegexp(TypeError, expected):
                Database(root, [Spec001, BadSpec])

        with TemporaryDirectory() as root:
            self.create_files(root)
            Database(root, [])
            Database(root, [Spec001])
            Database(root, [Spec001, Spec002])

    def test_update(self):
        Spec001, Spec002, BadSpec = self.get_specifications()

        with TemporaryDirectory() as root:
            self.create_files(root)
            result = Database(root, [Spec001]).update().data
            self.assertEqual(len(result), 5)
