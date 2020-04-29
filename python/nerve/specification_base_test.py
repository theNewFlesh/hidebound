from pathlib import Path
import unittest
import uuid

import nerve.specification_base as sb
from nerve.validators import ValidationError
# ------------------------------------------------------------------------------


class SpecificationBaseTests(unittest.TestCase):
    filepath = '/tmp/proj001/p-proj001_s-spec001_d-desc_v001/p-proj001_s-spec001_d-desc_v001.ext'

    class Foo(sb.SpecificationBase):
        def get_asset_path(self, filepath):
            return Path(filepath).parent

    def test_init(self):
        result = sb.SpecificationBase().name
        self.assertEqual(result, 'specificationbase')
        result = self.Foo().name
        self.assertEqual(result, 'foo')

    def test_get_asset_name(self):
        result = self.Foo().get_asset_name(self.filepath)
        expected = 'p-proj001_s-spec001_d-desc_v001'
        self.assertEqual(result, expected)

    def test_get_asset_path(self):
        class Bar(sb.SpecificationBase):
            pass
        expected = 'Method must be implemented in subclasses of SpecificationBase.'
        with self.assertRaisesRegexp(NotImplementedError, expected):
            Bar().get_asset_path(self.filepath)

        result = self.Foo().get_asset_path(self.filepath)
        expected = Path('/tmp/proj001/p-proj001_s-spec001_d-desc_v001')
        self.assertEqual(result, expected)

    def test_get_asset_id(self):
        result = self.Foo().get_asset_id(self.filepath)
        expected = str(uuid.uuid3(uuid.NAMESPACE_URL, '/tmp/proj001/p-proj001_s-spec001_d-desc_v001'))
        self.assertEqual(result, expected)

    def test_validate_filepath(self):
        self.Foo().validate_filepath(self.filepath)

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
        bad_descriptor_token = Path(root, bad_parent, filename)
        expected = 'Invalid asset directory name'
        with self.assertRaisesRegexp(ValidationError, expected):
            self.Foo().validate_filepath(bad_descriptor_token)

    def test_get_filename_metadata(self):
        result = self.Foo().get_filename_metadata(self.filepath)
        expected = dict(
            project='proj001',
            specification='spec001',
            descriptor='desc',
            version=1,
            extension='ext',
        )
        self.assertEqual(result, expected)


class OtherSpecificationBaseTests(unittest.TestCase):
    filepath = '/tmp/proj001/p-proj001_s-spec001_d-desc_v001/p-proj001_s-spec001_d-desc_v001.ext'

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
