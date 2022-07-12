from pathlib import Path
from tempfile import TemporaryDirectory
import re

import yaml

from hidebound.core.database_test_base import DatabaseTestBase
import hidebound.server.server_tools as hst
# ------------------------------------------------------------------------------


class ServerToolsTests(DatabaseTestBase):
    def test_setup_hidebound_directories(self):
        with TemporaryDirectory() as root:
            hst.setup_hidebound_directories(root)
            for folder in ['ingress', 'hidebound', 'archive']:
                self.assertTrue(Path(root, folder).is_dir())

    # ERRORS--------------------------------------------------------------------
    def test_get_config_error(self):
        result = hst.get_config_error().json['message']
        expected = 'Please supply a config dictionary.'
        self.assertRegex(result, expected)

    def test_get_initialization_error(self):
        result = hst.get_initialization_error().json['message']
        expected = 'Database not initialized. Please call initialize.'
        self.assertRegex(result, expected)

    def test_get_update_error(self):
        result = hst.get_update_error().json['message']
        expected = 'Database not updated. Please call update.'
        self.assertRegex(result, expected)

    def test_get_read_error(self):
        result = hst.get_read_error().json['message']
        expected = 'Please supply valid read params in the form '
        expected += r'\{"group_by_asset": BOOL\}\.'
        self.assertRegex(result, expected)

    def test_get_search_error(self):
        result = hst.get_search_error().json['message']
        expected = 'Please supply valid search params in the form '
        expected += r'\{"query": SQL query, "group_by_asset": BOOL\}\.'
        self.assertRegex(result, expected)

    def test_get_connection_error(self):
        result = hst.get_connection_error().json['message']
        expected = 'Database not connected.'
        self.assertRegex(result, expected)

    def test_error_to_response(self):
        error = TypeError('foo')
        result = hst.error_to_response(error)
        self.assertEqual(result.mimetype, 'application/json')
        self.assertEqual(result.json['error'], 'TypeError')
        self.assertEqual(result.json['args'], ['foo'])
        self.assertEqual(result.json['message'], 'TypeError(\n    foo\n)')
        self.assertEqual(result.json['code'], 500)

    def test_error_to_response_dict(self):
        arg = {
            'bars': {
                f'bar-{i:02d}': {
                    f'bar-{i:02d}': 'banana'
                } for i in range(3)
            },
            'foos': [['pizza'] * 3] * 3,
        }
        error = TypeError(arg, arg, 'arg2')
        result = hst.error_to_response(error)

        expected = r'''
TypeError(
    {'bars': "{'bar-00': {'bar-00': 'banana'},\n"
         " 'bar-01': {'bar-01': 'banana'},\n"
         " 'bar-02': {'bar-02': 'banana'}}"}
    {'foos': "[['pizza', 'pizza', 'pizza'],\n"
         " ['pizza', 'pizza', 'pizza'],\n"
         " ['pizza', 'pizza', 'pizza']]"}
    {'bars': "{'bar-00': {'bar-00': 'banana'},\n"
         " 'bar-01': {'bar-01': 'banana'},\n"
         " 'bar-02': {'bar-02': 'banana'}}"}
    {'foos': "[['pizza', 'pizza', 'pizza'],\n"
         " ['pizza', 'pizza', 'pizza'],\n"
         " ['pizza', 'pizza', 'pizza']]"}
    arg2
)'''[1:]

        self.assertEqual(result.mimetype, 'application/json')
        self.assertEqual(result.json['error'], 'TypeError')
        self.assertEqual(result.json['args'][0], str(arg))
        self.assertEqual(result.json['args'][1], str(arg))
        self.assertEqual(result.json['args'][2], 'arg2')
        self.assertEqual(result.json['message'], expected)
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
        hst.parse_json_file_content(content)

        expected = 'File header is not JSON. Header: '
        expected += 'data:application/text;base64.'
        content = re.sub('json', 'text', content)
        with self.assertRaisesRegexp(ValueError, expected):
            hst.parse_json_file_content(content)

    # DASH-TOOLS----------------------------------------------------------------
    def test_get_progress(self):
        with TemporaryDirectory() as root:
            log = Path(root, 'test.log')

            result = hst.get_progress(log)
            expected = dict(progress=1.0, message='unknown state')
            self.assertEqual(result, expected)

            with open(log, 'w') as f:
                f.write(
                    '{"line": "first"}\n{"line": "middle"}\n{"line": "last"}'
                )
            result = hst.get_progress(log)
            expected['line'] = 'last'
            self.assertEqual(result, expected)


def test_request(env, extension, config, client):
    store = {}
    url = 'http://127.0.0.1/api/initialize'
    params = dict(
        ingress_directory=config['ingress_directory'],
        staging_directory=config['staging_directory'],
        specification_files=config['specification_files'],
    )
    result = hst.request(store, url, params, client)
    assert result == {'message': 'Database initialized.'}
    assert store == {}


def test_request_error(env, extension, config, client):
    store = {}
    url = 'http://127.0.0.1/api/initialize'
    params = dict(foo='bar')
    result = hst.request(store, url, params, client)
    assert store['content'] == result
    assert store['content']['code'] == 500


def test_search(env, extension, config, client):
    store = {}
    query = 'SELECT * FROM data'
    result = hst.search(store, query, False, client)
    assert 'content' in result.keys()
    assert result['query'] == query


def test_format_config_exporters(config):
    expected = dict(
        local_disk=dict(
            target_directory='/tmp/mnt/archive',
            metadata_types=['asset', 'file']
        ),
        s3=dict(
            access_key='access_key',
            secret_key='secret_key',
            bucket='bucket',
            region='region',
            metadata_types=['asset', 'file']
        ),
        girder=dict(
            api_key='api_key',
            root_id='root_id',
            root_type='root_type',
            host='host',
            port=80,
            metadata_types=['asset', 'file']
        )
    )
    config['exporters'] = expected
    result = hst.format_config(config)
    result = yaml.safe_load(result['exporters'])

    expected['s3']['access_key'] = 'REDACTED'
    expected['s3']['secret_key'] = 'REDACTED'
    expected['girder']['api_key'] = 'REDACTED'
    expected['girder']['root_id'] = 'REDACTED'
    assert result == expected


def test_format_config_specs(config):
    key = 'specification_files'
    config[key] = ['/tmp/foo.py', '/tmp/bar.py']
    result = hst.format_config(config)[key]

    expected = '''
- /tmp/foo.py
- /tmp/bar.py
'''[1:-1]
    assert result == expected


def test_format_config_webhooks(config):
    result = hst.format_config(config)
    result = yaml.safe_load(result['webhooks'])[0]['url']
    assert result == 'REDACTED'


def test_format_config_ellipsis(config):
    result = hst.format_config(config)
    for val in result.values():
        assert re.search(r'\.\.\.', val) is None


def test_format_config_extra_keys(config):
    config['2'] = 'bar'
    config['1'] = 'foo'
    result = hst.format_config(config)

    key, val = result.popitem()
    assert key == '2'
    assert val == 'bar'

    key, val = result.popitem()
    assert key == '1'
    assert val == 'foo'
