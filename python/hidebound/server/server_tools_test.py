import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from hidebound.core.database_test_base import DatabaseTestBase
import hidebound.server.server_tools as server_tools
# ------------------------------------------------------------------------------


class ServerToolsTests(DatabaseTestBase):
    def test_setup_hidebound_directory(self):
        with TemporaryDirectory() as root:
            server_tools.setup_hidebound_directory(root)

            hb_dir = Path(root, 'hidebound')
            self.assertTrue(hb_dir.is_dir())

            specs = Path(hb_dir, 'specifications')
            self.assertTrue(specs.is_dir())

            config = Path(hb_dir, 'hidebound_config.json')
            self.assertTrue(config.is_file())

            with open(config) as f:
                result = json.load(f)
            expected = {
                'root_directory': '/mnt/storage/projects',
                'hidebound_directory': '/mnt/storage/hidebound',
                'specification_files': [],
                'include_regex': '',
                'exclude_regex': r'\.DS_Store',
                'write_mode': 'copy'
            }
            self.assertEqual(result, expected)

    # APP-----------------------------------------------------------------------
    def test_get_app(self):
        server_tools.get_app(__name__)
        # self.assertEqual(result._database, None)
        # self.assertEqual(result._config, {})
        # self.assertEqual(result._config_path, '')

    # ERRORS--------------------------------------------------------------------
    def test_get_config_error(self):
        result = server_tools.get_config_error().json['message']
        expected = 'Please supply a config dictionary.'
        self.assertRegex(result, expected)

    def test_get_initialization_error(self):
        result = server_tools.get_initialization_error().json['message']
        expected = 'Database not initialized. Please call initialize.'
        self.assertRegex(result, expected)

    def test_get_update_error(self):
        result = server_tools.get_update_error().json['message']
        expected = 'Database not updated. Please call update.'
        self.assertRegex(result, expected)

    def test_get_read_error(self):
        result = server_tools.get_read_error().json['message']
        expected = 'Please supply valid read params in the form '
        expected += r'\{"group_by_asset": BOOL\}\.'
        self.assertRegex(result, expected)

    def test_get_search_error(self):
        result = server_tools.get_search_error().json['message']
        expected = 'Please supply valid search params in the form '
        expected += r'\{"query": SQL query, "group_by_asset": BOOL\}\.'
        self.assertRegex(result, expected)

    def test_error_to_response(self):
        error = TypeError('foo')
        result = server_tools.error_to_response(error)
        self.assertEqual(result.mimetype, 'application/json')
        self.assertEqual(result.json['error'], 'TypeError')
        self.assertEqual(result.json['args'], ['foo'])
        self.assertEqual(result.json['message'], 'TypeError(\n    foo\n)')
        self.assertEqual(result.json['code'], 500)

    # TOOLS---------------------------------------------------------------------
    def test_parse_json_file_content(self):
        content = '''data:application/json;base64,\
ewogICAgInJvb3RfZGlyZWN0b3J5IjogIi90bXAvYmFnZWxoYXQiLAogICAgImhpZGVib3VuZF9kaXJ\
lY3RvcnkiOiAiL3RtcC9zaWxseWNhdHMvaGlkZWJvdW5kIiwKICAgICJzcGVjaWZpY2F0aW9uX2ZpbG\
VzIjogWwogICAgICAgICIvcm9vdC9oaWRlYm91bmQvcHl0aG9uL2hpZGVib3VuZC9hd2Vzb21lX3NwZ\
WNpZmljYXRpb25zLnB5IgogICAgXSwKICAgICJpbmNsdWRlX3JlZ2V4IjogIiIsCiAgICAiZXhjbHVk\
ZV9yZWdleCI6ICJcXC5EU19TdG9yZXx5b3VyLW1vbSIsCiAgICAid3JpdGVfbW9kZSI6ICJjb3B5Igp\
9Cg=='''
        server_tools.parse_json_file_content(content)

        expected = 'File header is not JSON. Header: '
        expected += 'data:application/text;base64.'
        content = re.sub('json', 'text', content)
        with self.assertRaisesRegexp(ValueError, expected):
            server_tools.parse_json_file_content(content)
