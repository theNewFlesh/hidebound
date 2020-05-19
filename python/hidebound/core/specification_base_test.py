from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import uuid

import numpy as np
from schematics.exceptions import ValidationError
import skimage.io

import hidebound.core.specification_base as sb
import hidebound.core.traits as traits
# ------------------------------------------------------------------------------


class SpecificationBaseTests(unittest.TestCase):
    filepath = '/tmp/proj001/p-proj001_s-spec001_d-desc_v001/'
    filepath += 'p-proj001_s-spec001_d-desc_v001.ext'

    class Foo(sb.SpecificationBase):
        file_traits = {
            'width': traits.get_image_width,
            'height': traits.get_image_height,
            'channels': traits.get_image_channels,
        }

        def get_asset_path(self, filepath):
            return Path(filepath).parent

    class Bar(sb.FileSpecificationBase):
        def get_asset_path(self, filepath):
            return Path(filepath)

    def test_init(self):
        sb.SpecificationBase()

    def test_get_asset_name(self):
        result = self.Foo().get_asset_name(self.filepath)
        expected = 'p-proj001_s-spec001_d-desc_v001'
        self.assertEqual(result, expected)

    def test_get_asset_path(self):
        class Bar(sb.SpecificationBase):
            pass
        expected = 'Method must be implemented in subclasses of '
        expected += 'SpecificationBase.'
        with self.assertRaisesRegexp(NotImplementedError, expected):
            Bar().get_asset_path(self.filepath)

        result = self.Foo().get_asset_path(self.filepath)
        expected = Path('/tmp/proj001/p-proj001_s-spec001_d-desc_v001')
        self.assertEqual(result, expected)

    def test_get_asset_id(self):
        result = self.Foo().get_asset_id(self.filepath)
        expected = str(
            uuid.uuid3(
                uuid.NAMESPACE_URL,
                '/tmp/proj001/p-proj001_s-spec001_d-desc_v001'
            )
        )
        self.assertEqual(result, expected)

    def test_validate_filepath(self):
        self.Foo().validate_filepath(self.filepath)
        self.Bar().validate_filepath(self.filepath)

        root = '/tmp/proj001'
        parent = 'p-proj001_s-spec001_d-desc_v001'
        filename = 'p-proj001_s-spec001_d-desc_v001.ext'

        bad = 'p-proj001_spec001_d-desc_v001.ext'
        bad_filename_indicator = Path(root, parent, bad)
        expected = 'Illegal specification field indicator'
        with self.assertRaisesRegexp(ValidationError, expected):
            self.Foo().validate_filepath(bad_filename_indicator)

        bad = 'p-proj001_s-spec001_d-PIZZA_v001.ext'
        bad_parent = 'p-proj001_s-spec001_d-PIZZA_v001'
        bad_descriptor_token = Path(root, bad_parent, bad)
        expected = 'Illegal descriptor field token'
        with self.assertRaisesRegexp(ValidationError, expected):
            self.Foo().validate_filepath(bad_descriptor_token)

        bad_parent = 'p-proj001_s-spec001_d-pizza_v001'
        bad_parent = Path(root, bad_parent, filename)
        expected = 'Invalid asset directory name'
        with self.assertRaisesRegexp(ValidationError, expected):
            self.Foo().validate_filepath(bad_parent)

        bad_parent_token = 'p-proj001_s-spec001_d-pizza_v01'
        bad_parent_token = Path(root, bad_parent_token, filename)
        expected = 'Illegal version field token'
        with self.assertRaisesRegexp(ValidationError, expected):
            self.Foo().validate_filepath(bad_parent_token)

    def test_get_filename_traits(self):
        result = self.Foo().get_filename_traits(self.filepath)
        expected = dict(
            project='proj001',
            specification='spec001',
            descriptor='desc',
            version=1,
            extension='ext',
        )
        self.assertEqual(result, expected)

    def test_get_file_traits(self):
        with TemporaryDirectory() as root:
            img = np.zeros((5, 4, 3), dtype=np.uint8)
            filepath = Path(root, 'foo.png')
            skimage.io.imsave(filepath.as_posix(), img)

            result = self.Foo().get_file_traits(filepath)
            expected = dict(width=4, height=5, channels=3)
            self.assertEqual(result, expected)

    def test_get_file_traits_error(self):
        with TemporaryDirectory() as root:
            filepath = Path(root, 'foo.txt')
            with open(filepath, 'w') as f:
                f.write('')

            result = self.Foo().get_file_traits(filepath)
            self.assertRegex(result['width_error'], 'ValueError')
            self.assertRegex(result['height_error'], 'ValueError')
            self.assertRegex(result['channels_error'], 'ValueError')

    def test_get_traits(self):
        with TemporaryDirectory() as root:
            img = np.zeros((5, 4, 3), dtype=np.uint8)
            name = 'p-proj001_s-spec001_d-desc_v001.png'
            filepath = Path(root, name)
            skimage.io.imsave(filepath.as_posix(), img)

            result = self.Foo().get_traits(filepath)
            expected = dict(
                project='proj001',
                specification='spec001',
                descriptor='desc',
                version=1,
                extension='png',
                width=4,
                height=5,
                channels=3
            )
            self.assertEqual(result, expected)

    def test_get_traits_error(self):
        with TemporaryDirectory() as root:
            name = 'p-proj001_FOOBAR_d-desc_v001.png'
            filepath = Path(root, name)
            with open(filepath, 'w') as f:
                f.write('')

            result = self.Foo().get_traits(filepath).keys()
            result = sorted(result)
            expected = [
                'channels_error', 'filename_error', 'height_error',
                'width_error'
            ]
            self.assertEqual(result, expected)

            result = self.Foo().get_traits(filepath)
            self.assertRegex(
                result['filename_error'],
                'Illegal specification field indicator'
            )

            name = 'p-proj001_s-spec001_d-desc_v001.png'
            filepath = Path(root, name)
            with open(filepath, 'w') as f:
                f.write('')

            result = self.Foo().get_traits(filepath)
            good = dict(
                project='proj001',
                specification='spec001',
                descriptor='desc',
                version=1,
                extension='png',
            )
            for k, v in good.items():
                self.assertEqual(result[k], good[k])

            bad = ['width_error', 'height_error', 'channels_error']
            for k in bad:
                self.assertRegex(result[k], 'ValueError')


class OtherSpecificationBaseTests(unittest.TestCase):
    filepath = '/tmp/proj001/p-proj001_s-spec001_d-desc_v001/'
    filepath += 'p-proj001_s-spec001_d-desc_v001.ext'

    def test_file_specification_base(self):
        result = sb.FileSpecificationBase()
        self.assertEqual(result.asset_type, 'file')
        result = result.get_asset_path(self.filepath)
        expected = Path(
            '/tmp/proj001/p-proj001_s-spec001_d-desc_v001',
            'p-proj001_s-spec001_d-desc_v001.ext'
        )
        self.assertEqual(result, expected)

    def test_sequence_specification_base(self):
        result = sb.SequenceSpecificationBase()
        self.assertEqual(result.asset_type, 'sequence')
        result = result.get_asset_path(self.filepath)
        expected = Path('/tmp/proj001/p-proj001_s-spec001_d-desc_v001')
        self.assertEqual(result, expected)

    def test_complex_specification_base(self):
        result = sb.ComplexSpecificationBase()
        self.assertEqual(result.asset_type, 'complex')
