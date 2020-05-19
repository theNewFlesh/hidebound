import json
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory

import numpy as np

from hidebound.database_test_base import DatabaseTestBase
import hidebound.app as application
import hidebound.components as components
import hidebound.tools as tools
# ------------------------------------------------------------------------------


class AppTests(DatabaseTestBase):
    def setUp(self):
        # setup files and dirs
        self.tempdir = TemporaryDirectory()
        temp = self.tempdir.name
        self.hb_root = Path(temp, 'hidebound').as_posix()
        os.makedirs(self.hb_root)

        self.root = Path(temp, 'projects').as_posix()
        os.makedirs(self.root)

        self.create_files(self.root)

        # setup app
        self.context = application.APP.server.app_context()
        self.context.push()

        self.app = self.context.app
        self.app._database = None
        self.app._config = None

        self.client = self.app.test_client()
        self.app.config['TESTING'] = True

        self.specs = tools.relative_path(
            __file__,
            '../hidebound/test_specifications.py'
        ).absolute().as_posix()

    def tearDown(self):
        self.context.pop()
        self.tempdir.cleanup()

    # SETUP---------------------------------------------------------------------
    def test_setup_hidebound_directory(self):
        with TemporaryDirectory() as root:
            application.setup_hidebound_directory(root)

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

    # CLIENT--------------------------------------------------------------------
    def test_serve_stylesheet(self):
        params = dict(
            COLOR_SCHEME=components.COLOR_SCHEME,
            FONT_FAMILY=components.FONT_FAMILY,
        )
        expected = components.render_template('style.css.j2', params)
        result = next(self.client.get('/static/style.css').response)
        self.assertEqual(result, expected)

    # INITIALIZE----------------------------------------------------------------
    def test_initialize(self):
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        result = self.client.post('/api/initialize', json=config)
        result = result.json['message']
        expected = 'Database initialized.'
        self.assertEqual(result, expected)

    def test_initialize_no_config(self):
        result = self.client.post('/api/initialize').json['message']
        expected = 'Please supply a config dictionary.'
        self.assertRegex(result, expected)

    def test_initialize_bad_config_type(self):
        bad_config = '["a", "b"]'
        result = self.client.post('/api/initialize', json=bad_config)
        result = result.json['message']
        expected = 'Please supply a config dictionary.'
        self.assertRegex(result, expected)

    def test_initialize_bad_config(self):
        config = dict(
            root_directory='/foo/bar',
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        result = self.client.post('/api/initialize', json=config)
        result = result.json['message']
        expected = '/foo/bar is not a directory or does not exist.'
        self.assertRegex(result, expected)

    # UPDATE--------------------------------------------------------------------
    def test_update(self):
        # init database
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)

        # call update
        result = self.client.post('/api/update').json['message']
        expected = 'Database updated.'
        self.assertEqual(result, expected)

    def test_update_no_init(self):
        result = self.client.post('/api/update').json['message']
        expected = 'Database not initialized. Please call initialize.'
        self.assertRegex(result, expected)

    # READ----------------------------------------------------------------------
    def test_read(self):
        # init database
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.client.post('/api/update')

        # call read
        result = self.client.post('/api/read').json['response']
        expected = self.app._database.read()\
            .replace({np.nan: None})\
            .to_dict(orient='records')
        self.assertEqual(result, expected)

    def test_read_group_by_asset(self):
        # init database
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.client.post('/api/update')

        # good params
        params = json.dumps({'group_by_asset': True})
        result = self.client.post('/api/read', json=params).json['response']
        expected = self.app._database.read(group_by_asset=True)\
            .replace({np.nan: None})\
            .to_dict(orient='records')
        self.assertEqual(result, expected)

        # bad params
        params = json.dumps({'foo': True})
        result = self.client.post('/api/read', json=params).json['message']
        expected = 'Please supply valid read params in the form '
        expected += r'\{"group_by_asset": BOOL\}\.'
        self.assertRegex(result, expected)

        params = json.dumps({'group_by_asset': 'foo'})
        result = self.client.post('/api/read', json=params).json['message']
        expected = 'Please supply valid read params in the form '
        expected += r'\{"group_by_asset": BOOL\}\.'
        self.assertRegex(result, expected)

    def test_read_no_init(self):
        result = self.client.post('/api/read').json['message']
        expected = 'Database not initialized. Please call initialize.'
        self.assertRegex(result, expected)

    def test_read_no_update(self):
        # init database
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)

        # call read
        result = self.client.post('/api/read').json['message']
        expected = 'Database not updated. Please call update.'
        self.assertRegex(result, expected)

    # SEARCH--------------------------------------------------------------------
    def test_search(self):
        # init database
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.client.post('/api/update')

        # call search
        query = 'SELECT * FROM data WHERE specification == "spec001"'
        temp = {'query': query}
        temp = json.dumps(temp)
        result = self.client.post('/api/search', json=temp).json['response']
        expected = self.app._database.search(query)\
            .replace({np.nan: None})\
            .to_dict(orient='records')
        self.assertEqual(result, expected)

    def test_search_group_by_asset(self):
        # init database
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.client.post('/api/update')

        # call search
        query = 'SELECT * FROM data WHERE asset_type == "sequence"'
        temp = {'query': query, 'group_by_asset': True}
        temp = json.dumps(temp)
        result = self.client.post('/api/search', json=temp).json['response']
        expected = self.app._database.search(query, group_by_asset=True)\
            .replace({np.nan: None})\
            .to_dict(orient='records')
        self.assertEqual(result, expected)

    def test_search_no_query(self):
        result = self.client.post('/api/search').json['message']
        expected = 'Please supply valid search params in the form '
        expected += r'\{"query": SQL query, "group_by_asset": BOOL\}\.'
        self.assertRegex(result, expected)

    def test_search_bad_json(self):
        query = {'foo': 'bar'}
        query = json.dumps(query)
        result = self.client.post('/api/search', json=query).json['message']
        expected = 'Please supply valid search params in the form '
        expected += r'\{"query": SQL query, "group_by_asset": BOOL\}\.'
        self.assertRegex(result, expected)

    def test_search_bad_group_by_asset(self):
        params = dict(
            query='SELECT * FROM data WHERE asset_type == "sequence"',
            group_by_asset='foo'
        )
        params = json.dumps(params)
        result = self.client.post('/api/search', json=params).json['message']
        expected = 'Please supply valid search params in the form '
        expected += r'\{"query": SQL query, "group_by_asset": BOOL\}\.'
        self.assertRegex(result, expected)

    def test_search_bad_query(self):
        # init database
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.client.post('/api/update')

        # call search
        query = {'query': 'SELECT * FROM data WHERE foo == "bar"'}
        query = json.dumps(query)
        result = self.client.post('/api/search', json=query).json['error']
        expected = 'PandaSQLException'
        self.assertEqual(result, expected)

    def test_search_no_init(self):
        query = {'query': 'SELECT * FROM data WHERE specification == "spec001"'}
        query = json.dumps(query)
        result = self.client.post('/api/search', json=query).json['message']
        expected = 'Database not initialized. Please call initialize.'
        self.assertRegex(result, expected)

    def test_search_no_update(self):
        # init database
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)

        # call search
        query = {'query': 'SELECT * FROM data WHERE specification == "spec001"'}
        query = json.dumps(query)
        result = self.client.post('/api/search', json=query).json['message']
        expected = 'Database not updated. Please call update.'
        self.assertRegex(result, expected)

    # CREATE--------------------------------------------------------------------
    def test_create(self):
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.client.post('/api/update')

        data = Path(self.hb_root, 'data')
        meta = Path(self.hb_root, 'metadata')
        self.assertFalse(os.path.exists(data))
        self.assertFalse(os.path.exists(meta))

        result = self.client.post('/api/create').json['message']
        expected = 'Hidebound data created.'
        self.assertEqual(result, expected)
        self.assertTrue(os.path.exists(data))
        self.assertTrue(os.path.exists(meta))

    def test_create_no_update(self):
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)

        result = self.client.post('/api/create').json['message']
        expected = 'Database not updated. Please call update.'
        self.assertRegex(result, expected)

    def test_create_no_init(self):
        result = self.client.post('/api/create').json['message']
        expected = 'Database not initialized. Please call initialize.'
        self.assertRegex(result, expected)

    # DELETE--------------------------------------------------------------------
    def test_delete(self):
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.client.post('/api/update')
        self.client.post('/api/create')

        data = Path(self.hb_root, 'data')
        meta = Path(self.hb_root, 'metadata')
        self.assertTrue(os.path.exists(data))
        self.assertTrue(os.path.exists(meta))

        result = self.client.post('/api/delete').json['message']
        expected = 'Hidebound data deleted.'
        self.assertEqual(result, expected)
        self.assertFalse(os.path.exists(data))
        self.assertFalse(os.path.exists(meta))

    def test_delete_no_create(self):
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)

        result = self.client.post('/api/delete').json['message']
        expected = 'Hidebound data deleted.'
        self.assertEqual(result, expected)

        data = Path(self.hb_root, 'data')
        meta = Path(self.hb_root, 'metadata')
        self.assertFalse(os.path.exists(data))
        self.assertFalse(os.path.exists(meta))

    def test_delete_no_init(self):
        result = self.client.post('/api/delete').json['message']
        expected = 'Database not initialized. Please call initialize.'
        self.assertRegex(result, expected)

    # ERRORS--------------------------------------------------------------------
    def test_get_config_error(self):
        result = application.get_config_error().json['message']
        expected = 'Please supply a config dictionary.'
        self.assertRegex(result, expected)

    def test_get_initialization_error(self):
        result = application.get_initialization_error().json['message']
        expected = 'Database not initialized. Please call initialize.'
        self.assertRegex(result, expected)

    def test_get_update_error(self):
        result = application.get_update_error().json['message']
        expected = 'Database not updated. Please call update.'
        self.assertRegex(result, expected)

    def test_get_read_error(self):
        result = application.get_read_error().json['message']
        expected = 'Please supply valid read params in the form '
        expected += r'\{"group_by_asset": BOOL\}\.'
        self.assertRegex(result, expected)

    def test_get_search_error(self):
        result = application.get_search_error().json['message']
        expected = 'Please supply valid search params in the form '
        expected += r'\{"query": SQL query, "group_by_asset": BOOL\}\.'
        self.assertRegex(result, expected)

    # ERROR-HANDLERS------------------------------------------------------------
    def test_error_to_response(self):
        error = TypeError('foo')
        result = application.error_to_response(error)
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
        application.parse_json_file_content(content)

        expected = 'File header is not JSON. Header: '
        expected += 'data:application/text;base64.'
        content = re.sub('json', 'text', content)
        with self.assertRaisesRegexp(ValueError, expected):
            application.parse_json_file_content(content)
