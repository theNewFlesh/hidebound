from pathlib import Path
import os
import re
from tempfile import TemporaryDirectory
import time
import unittest

from pandas import DataFrame

from nerve.database import Database
from nerve.specification_base import Specification
# ------------------------------------------------------------------------------


class DatabaseTests(unittest.TestCase):
    columns = [
        'project',
        'specification',
        'descriptor',
        'version',
        'coordinate',
        'frame',
        'extension',
        'asset_name',
        'filename',
        'fullpath',
        'error'
    ]

    def get_fullpaths(self, root):
        assets = [
            [
                'p-proj001_s-spec001_d-pizza_v001_c000-001_f0001.png',
                'p-proj001_s-spec001_d-pizza_v001_c000-001_f0002.png',
                'p-proj001_s-spec001_d-pizza_v001_c000-001_f0003.png',
            ],[
                'p-proj001_s-spec001_d-pizza_v002_c000-000_f0001.png',
                'p-proj001_s-spec001_d-pizza_v002_c000-000_f0002.png',
                'p-proj001_s-spec001_d-pizza_v002_c000-000_f0003.png',
                'p-proj001_s-spec001_d-pizza_v002_c000-000_f0004.png'
            ],[
                'p-proj001_s-spec001_d-pizza_v002_c000-001_f0001.png',
                'p-proj001_s-spec001_d-pizza_v002_c000-001_f0002.png',
                'p-proj001_s-spec001_d-pizza_v002_c000-001_f0003.png',
                'p-proj001_s-spec001_d-pizza_v002_c000-001_f0004.png'
            ],[
                'p-proj001_s-spec001_d-kiwi_v003_c000-001_f0001.png',
                'p-proj001_s-spec001_d-pizza_v003_c000-001_f0002.png',
                'p-proj001_s-spec001_d-PIZZA_v003_c000-001_f0003.png',
                'p-proj001_s-spec001_d-pizza_v003_c000-001_f0004.png',
                'misc.txt',
            ],[
                'p-proj001_s-spec002_d-pizza_v001_f0000.exr',
                'p-proj001_s-spec002_d-pizza_v001_f0001.exr',
                'p-proj001_s-spec002_d-pizza_v001_f0002.exr',
            ],[
                'p-proj001_s-spec002_d-pizza_v002_f0001.exr',
                'p-proj001_s-spec002_d-pizza_v002_f0002.exr',
                'p-proj001_s-spec002_d-pizza_v002_f0003.exr',
                'proj001_s-spec002_pizza_v002_0004.exr',
            ],[
                'p-proj001_s-spec002_d-pizza_v002_f0001.exr',
                'proj001_s-spec002_pizza_v002_f0002.exr',
                'p-proj001_s-spec002_d-pizza_v002_f0003.exr',
                'p-proj001_s-spec002_d-pizza_v002'
            ],[
                'p-proj001_s-spec002_d-pizza_v003_f0001.exr',
                'p-proj001_s-spec002_d-pizza_v003_f0002.exr',
                'p-proj001_s-spec002_pizza_v003_f0003.exr',
                'p-proj001_s-spec002_d-pizza_v003_f0004.exr',
            ],[
                'p-proj002_s-vdb001_d-bagel_v001.vdb',
                'p-proj002_s-vdb001_d-bagel_v002.vdb',
                'p-proj002_s-vdb001_d-bagel_v003.vdb',
            ],
        ]

        # convert to fullpaths
        output = []
        for asset in assets:
            files = asset[0].split('_')
            dir_ = '_'.join(files[:4])
            dir_ = os.path.splitext(dir_)[0]
            if 'vdb' in dir_:
                dir_ = ''

            files = [re.sub('.-', '', x) for x in files]
            parent = Path(root, *files[:3], dir_)

            for filename in asset:
                fullpath = Path(parent, filename)
                output.append(fullpath)
        return output

    def create_files(self, root):
        fullpaths = self.get_fullpaths(root)
        for fullpath in fullpaths:
            os.makedirs(fullpath.parent, exist_ok=True)
            with open(fullpath, 'w') as f:
                f.write('')
        return fullpaths

    def get_specifications(self):
        class Spec001(Specification):
            name = 'spec001'
            fields = [
                'project',
                'specification',
                'descriptor',
                'version',
                'coordinate',
                'frame',
                'extension',
            ]

        class Spec002(Specification):
            name = 'spec002'
            fields = [
                'project',
                'specification',
                'descriptor',
                'version',
                'frame',
                'extension',
            ]

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
            expected = 'Specification may only contain subclasses of'
            expected += ' Specification. Found: .*.'

            with self.assertRaisesRegexp(TypeError, expected):
                Database(root, [BadSpec])

            with self.assertRaisesRegexp(TypeError, expected):
                Database(root, [Spec001, BadSpec])

        with TemporaryDirectory() as root:
            self.create_files(root)
            Database(root, [])
            Database(root, [Spec001])
            Database(root, [Spec001, Spec002])

    def test_update_get_spec(self):
        Spec001, Spec002, BadSpec = self.get_specifications()

        with TemporaryDirectory() as root:
            self.create_files(root)
            result = Database(root, [Spec001]).update().data
            result = result.groupby('specification').count()
            self.assertEqual(result.fullpath, 15)
            self.assertEqual(result.error, 1)

    def test_update_no_files(self):
        Spec001, Spec002, BadSpec = self.get_specifications()

        with TemporaryDirectory() as root:
            result = Database(root, [Spec001]).update().data
            self.assertEqual(len(result), 0)
            self.assertEqual(result.columns.tolist(), self.columns)
