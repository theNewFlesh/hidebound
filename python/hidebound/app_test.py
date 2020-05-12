import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from hidebound.database_test_base import DatabaseTestBase
import hidebound.app as application
import hidebound.tools as tools
# ------------------------------------------------------------------------------


class AppTests(DatabaseTestBase):
    def setUp(self):
        # setup files and dirs
        self.tempdir = TemporaryDirectory()
        temp = self.tempdir.name
        self.hb_root = Path(temp, 'hb_root').as_posix()
        os.makedirs(self.hb_root)

        self.root = Path(temp, 'projects').as_posix()
        os.makedirs(self.root)

        self.create_files(self.root)

        # setup app
        self.context = application.app.app_context()
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

    # INITIALIZE----------------------------------------------------------------
    def test_initialize(self):
        config = dict(
            root_directory=self.root,
            hidebound_parent_directory=self.hb_root,
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
            hidebound_parent_directory=self.hb_root,
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
            hidebound_parent_directory=self.hb_root,
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
            hidebound_parent_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.client.post('/api/update')

        # call read
        result = self.client.post('/api/read').json
        expected = self.app._database.read()\
            .replace({np.nan: None})\
            .to_dict(orient='records')
        self.assertEqual(result, expected)

    def test_read_no_init(self):
        result = self.client.post('/api/read').json['message']
        expected = 'Database not initialized. Please call initialize.'
        self.assertRegex(result, expected)

    def test_read_no_update(self):
        # init database
        config = dict(
            root_directory=self.root,
            hidebound_parent_directory=self.hb_root,
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
            hidebound_parent_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.client.post('/api/update')

        # call search
        query = 'SELECT * FROM data WHERE specification == "spec001"'
        temp = {'query': query}
        temp = json.dumps(temp)
        result = self.client.post('/api/search', json=temp).json
        expected = self.app._database.search(query)\
            .replace({np.nan: None})\
            .to_dict(orient='records')
        self.assertEqual(result, expected)

    def test_search_no_query(self):
        result = self.client.post('/api/search').json['message']
        expected = 'Please supply a valid query of the form {"query": SQL}.'
        self.assertRegex(result, expected)

    def test_search_bad_json(self):
        query = {'foo': 'bar'}
        query = json.dumps(query)
        result = self.client.post('/api/search', json=query).json['message']
        expected = 'Please supply a valid query of the form {"query": SQL}.'
        self.assertRegex(result, expected)

    def test_search_bad_query(self):
        # init database
        config = dict(
            root_directory=self.root,
            hidebound_parent_directory=self.hb_root,
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
            hidebound_parent_directory=self.hb_root,
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
            hidebound_parent_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.client.post('/api/update')

        data = Path(self.hb_root, 'hidebound', 'data')
        meta = Path(self.hb_root, 'hidebound', 'metadata')
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
            hidebound_parent_directory=self.hb_root,
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
            hidebound_parent_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)
        self.client.post('/api/update')
        self.client.post('/api/create')

        data = Path(self.hb_root, 'hidebound', 'data')
        meta = Path(self.hb_root, 'hidebound', 'metadata')
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
            hidebound_parent_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/initialize', json=config)

        result = self.client.post('/api/delete').json['message']
        expected = 'Hidebound data deleted.'
        self.assertEqual(result, expected)

        data = Path(self.hb_root, 'hidebound', 'data')
        meta = Path(self.hb_root, 'hidebound', 'metadata')
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

    def test_get_query_error(self):
        result = application.get_query_error().json['message']
        expected = 'Please supply a valid query of the form {"query": SQL}.'
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
