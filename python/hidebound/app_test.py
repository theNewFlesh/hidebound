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

    # ERROR-HANDLERS------------------------------------------------------------
    def test_error_to_response(self):
        error = TypeError('foo')
        result = application.error_to_response(error)
        self.assertEqual(result.mimetype, 'application/json')
        self.assertEqual(result.json['error'], 'TypeError')
        self.assertEqual(result.json['args'], ['foo'])
        self.assertEqual(result.json['message'], 'TypeError(\n    foo\n)')
        self.assertEqual(result.json['code'], 500)
