import unittest
from pyparsing import Group, ParseException
import pytest
from nerve.parser import AssetNameParser
# ------------------------------------------------------------------------------


class ParserTests(unittest.TestCase):
    def test_init(self):
        with self.assertRaisesRegexp(ValueError, 'Fields cannot be empty.'):
            AssetNameParser([])

        with self.assertRaisesRegexp(ValueError, 'Fields cannot contain duplicates.'):
            AssetNameParser(['foo', 'foo'])

        with self.assertRaisesRegexp(ValueError, "Illegal fields found: \['foo', 'bar'\]"):
            AssetNameParser(['project', 'specification', 'foo', 'bar'])

        err = 'Illegal field order: Extension field must be last if it is included in fields.'
        with self.assertRaisesRegexp(ValueError, err):
            AssetNameParser(['project', 'specification', 'extension', 'descriptor'])

        fields = ['project', 'specification', 'version']
        result = AssetNameParser(fields)
        self.assertEqual(result._fields, fields)

        fields = ['specification', 'version', 'project', 'frame']
        result = AssetNameParser(fields)
        self.assertEqual(result._fields, fields)

    def test_parse_1(self):
        fields = ['project', 'specification', 'descriptor', 'version', 'frame', 'extension']
        name = 'p-proj002_s-spec062_d-desc_v099_f0078.exr'
        result = AssetNameParser(fields).parse(name)
        expected = dict(
            project='proj002',
            specification='spec062',
            descriptor='desc',
            version=99,
            frame=78,
            extension='exr',
        )
        self.assertEqual(result, expected)

    def test_parse_2(self):
        fields = ['project', 'specification', 'coordinate', 'version']
        name = 'p-proj002_s-spec062_c000-000-000_v099'
        result = AssetNameParser(fields).parse(name)
        expected = dict(
            project='proj002',
            specification='spec062',
            version=99,
            coordinate=[0, 0, 0]
        )
        self.assertEqual(result, expected)

    def test_parse_ignore_order(self):
        fields = ['project', 'specification', 'descriptor', 'version', 'frame', 'extension']
        name = 's-spec062_p-proj002_v099_d-desc_f0078.exr'
        result = AssetNameParser(fields).parse(name, ignore_order=True)
        expected = dict(
            project='proj002',
            specification='spec062',
            descriptor='desc',
            version=99,
            frame=78,
            extension='exr',
        )
        self.assertEqual(result, expected)

    def test_parse_bad_order(self):
        fields = ['project', 'specification', 'descriptor', 'version', 'frame', 'extension']
        name = 's-spec062_p-proj002_v099_d-desc_f0078.exr'
        with pytest.raises(ParseException) as e:
            AssetNameParser(fields).parse(name)
        expected = f'Incorrect field order in "{name}". Given field order: {fields}'
        self.assertEqual(str(e.value)[:len(expected)], expected)

    def test_parse_bad_indicator(self):
        fields = ['project', 'specification', 'descriptor', 'version', 'frame', 'extension']
        name = 'p-proj002_s-spec062_f-desc_v099_f0078.exr'
        msg = f'Illegal descriptor field indicator in "{name}". Expecting: "d-"'
        with self.assertRaisesRegexp(ParseException, msg):
            AssetNameParser(fields).parse(name)

        name = 'pp-proj002_s-spec062_d-desc_v099_f0078.exr'
        msg = f'Illegal project field indicator in "{name}". Expecting: "p-"'
        with self.assertRaisesRegexp(ParseException, msg):
            AssetNameParser(fields).parse(name)

    def test_parse_bad_token(self):
        fields = ['project', 'specification', 'descriptor', 'version', 'frame', 'extension']
        name = 'p-proj002_s-spec062_d-HELLO_v099_f0078.exr'
        msg = f'Illegal descriptor field token in "{name}". Expecting: .*'
        with self.assertRaisesRegexp(ParseException, msg):
            AssetNameParser(fields).parse(name)

    def test_to_string(self):
        pass

    def test_recurse_init(self):
        fields = ['project', 'specification', 'descriptor', 'version', 'frame', 'extension']
        expected = 'p-proj002_s-spec062_d-desc_v099_f0078.exr'
        parser = AssetNameParser(fields)
        result = parser.parse(expected)
        result = parser.to_string(result)
        self.assertEqual(result, expected)
