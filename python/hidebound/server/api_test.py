import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import flasgger as swg
import flask
import lunchbox.tools as lbt
import numpy as np
import yaml

from hidebound.core.database_test_base import DatabaseTestBase
from hidebound.exporters.mock_girder import MockGirderExporter
from hidebound.server.api import api_extension
# ------------------------------------------------------------------------------


class ApiExtensionTests(DatabaseTestBase):
    def setUp(self):
        # setup files and dirs
        self.temp_dir = TemporaryDirectory()
        temp = self.temp_dir.name
        self.hb_root = Path(temp, 'hidebound').as_posix()
        os.makedirs(self.hb_root)

        self.root = Path(temp, 'projects').as_posix()
        os.makedirs(self.root)

        self.target_dir = Path(temp, 'archive').as_posix()
        os.makedirs(self.target_dir)

        self.create_files(self.root)

        os.environ['HIDEBOUND_ROOT_DIRECTORY'] = self.root
        os.environ['HIDEBOUND_HIDEBOUND_DIRECTORY'] = self.hb_root
        os.environ['HIDEBOUND_EXPORTERS'] = yaml.safe_dump(dict(
            local_disk=dict(
                target_directory=self.target_dir,
                metadata_types=['asset', 'file', 'asset-chunk', 'file-chunk'],
            )
        ))

        # setup app
        app = flask.Flask(__name__)
        swg.Swagger(app)
        self.api = api_extension
        api_extension.init_app(app)
        self.context = app.app_context()
        self.context.push()

        self.app = self.context.app

        self.client = self.app.test_client()
        self.app.config['TESTING'] = True

        self.specs = lbt.relative_path(
            __file__,
            '../core/test_specifications.py'
        ).absolute().as_posix()

    def tearDown(self):
        self.context.pop()
        self.temp_dir.cleanup()

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
        expected = '/foo/bar is not a directory(.|\n)*or does not exist.'
        self.assertRegex(result, expected)

    # CREATE--------------------------------------------------------------------
    def test_create(self):
        config = dict(
            root_directory=self.root,
            hidebound_directory=self.hb_root,
            specification_files=[self.specs],
        )
        config = json.dumps(config)
        self.client.post('/api/update')

        data = Path(self.hb_root, 'content')
        meta = Path(self.hb_root, 'metadata')
        self.assertFalse(os.path.exists(data))
        self.assertFalse(os.path.exists(meta))

        result = self.client.post('/api/create').json['message']
        expected = 'Hidebound data created.'
        self.assertEqual(result, expected)
        self.assertTrue(os.path.exists(data))
        self.assertTrue(os.path.exists(meta))

    def test_create_no_update(self):
        result = self.client.post('/api/create').json['message']
        expected = 'Database not updated. Please call update.'
        self.assertRegex(result, expected)

    # READ----------------------------------------------------------------------
    def test_read(self):
        self.client.post('/api/update')

        # call read
        result = self.client.post('/api/read', json={}).json['response']
        expected = self.api.database.read()\
            .replace({np.nan: None})\
            .to_dict(orient='records')
        self.assertEqual(result, expected)

        # test general exceptions
        self.api.database = 'foo'
        result = self.client.post('/api/read', json={}).json['error']
        self.assertEqual(result, 'AttributeError')

    def test_read_group_by_asset(self):
        self.client.post('/api/update')

        # good params
        params = json.dumps({'group_by_asset': True})
        result = self.client.post('/api/read', json=params).json['response']
        expected = self.api.database.read(group_by_asset=True)\
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

    def test_read_no_update(self):
        result = self.client.post('/api/read', json={}).json['message']
        expected = 'Database not updated. Please call update.'
        self.assertRegex(result, expected)

    # UPDATE--------------------------------------------------------------------
    def test_update(self):
        result = self.client.post('/api/update').json['message']
        expected = 'Database updated.'
        self.assertEqual(result, expected)

    # DELETE--------------------------------------------------------------------
    def test_delete(self):
        self.client.post('/api/update')
        self.client.post('/api/create')

        data = Path(self.hb_root, 'content')
        meta = Path(self.hb_root, 'metadata')
        self.assertTrue(os.path.exists(data))
        self.assertTrue(os.path.exists(meta))

        result = self.client.post('/api/delete').json['message']
        expected = 'Hidebound data deleted.'
        self.assertEqual(result, expected)
        self.assertFalse(os.path.exists(data))
        self.assertFalse(os.path.exists(meta))

    def test_delete_no_create(self):
        result = self.client.post('/api/delete').json['message']
        expected = 'Hidebound data deleted.'
        self.assertEqual(result, expected)

        data = Path(self.hb_root, 'content')
        meta = Path(self.hb_root, 'metadata')
        self.assertFalse(os.path.exists(data))
        self.assertFalse(os.path.exists(meta))

    # EXPORT--------------------------------------------------------------------
    def test_export(self):
        result = os.listdir(self.target_dir)
        self.assertEqual(result, [])

        self.client.post('/api/update')
        self.client.post('/api/create')
        self.client.post('/api/export')

        result = os.listdir(self.target_dir)
        self.assertIn('content', result)
        self.assertIn('metadata', result)

    def test_export_error(self):
        self.client.post('/api/update')
        result = self.client.post('/api/export').json['message']
        expected = 'hidebound/content directory does not exist'
        self.assertRegex(result, expected)

    # SEARCH--------------------------------------------------------------------
    def test_search(self):
        self.client.post('/api/update')

        # call search
        query = 'SELECT * FROM data WHERE specification == "spec001"'
        temp = {'query': query}
        temp = json.dumps(temp)
        result = self.client.post('/api/search', json=temp)
        result = result.json['response']
        expected = self.api.database.search(query)\
            .replace({np.nan: None})\
            .to_dict(orient='records')
        self.assertEqual(result, expected)

    def test_search_group_by_asset(self):
        self.client.post('/api/update')

        # call search
        query = 'SELECT * FROM data WHERE asset_type == "sequence"'
        temp = {'query': query, 'group_by_asset': True}
        temp = json.dumps(temp)
        result = self.client.post('/api/search', json=temp).json['response']
        expected = self.api.database.search(query, group_by_asset=True)\
            .replace({np.nan: None})\
            .to_dict(orient='records')
        self.assertEqual(result, expected)

    def test_search_no_query(self):
        result = self.client.post('/api/search', json={}).json['message']
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
        self.client.post('/api/update', json={})

        # call search
        query = {'query': 'SELECT * FROM data WHERE foo == "bar"'}
        query = json.dumps(query)
        result = self.client.post('/api/search', json=query).json['error']
        expected = 'PandaSQLException'
        self.assertEqual(result, expected)

    def test_search_no_update(self):
        query = {'query': 'SELECT * FROM data WHERE specification == "spec001"'}
        query = json.dumps(query)
        result = self.client.post('/api/search', json=query).json['message']
        expected = 'Database not updated. Please call update.'
        self.assertRegex(result, expected)

    # WORKFLOW------------------------------------------------------------------
    def test_workflow(self):
        expected = ['update', 'create', 'export', 'delete']

        data = dict(workflow=expected)
        data = json.dumps(data)
        result = self.client.post('/api/workflow', json=data).json

        self.assertEqual(result['message'], 'Workflow completed.')
        self.assertEqual(result['workflow'], expected)

        data = Path(self.hb_root, 'content')
        self.assertFalse(os.path.exists(data))

        meta = Path(self.hb_root, 'metadata')
        self.assertFalse(os.path.exists(meta))

    def test_workflow_create(self):
        expected = ['update', 'create']

        data = dict(workflow=expected)
        data = json.dumps(data)
        result = self.client.post('/api/workflow', json=data).json

        self.assertEqual(result['message'], 'Workflow completed.')
        self.assertEqual(result['workflow'], expected)

        data = Path(self.hb_root, 'content')
        self.assertTrue(os.path.exists(data))

        meta = Path(self.hb_root, 'metadata')
        self.assertTrue(os.path.exists(meta))

    def test_workflow_bad_params(self):
        workflow = json.dumps({})
        result = self.client.post('/api/workflow', json=workflow).json
        self.assertEqual(result['error'], 'KeyError')

    def test_workflow_illegal_step(self):
        expected = ['update', 'create', 'foo', 'bar']
        data = dict(workflow=expected, config={})
        data = json.dumps(data)
        result = self.client.post('/api/workflow', json=data).json
        self.assertEqual(result['error'], 'ValueError')

        expected = "Found illegal workflow steps: ['bar', 'foo']. "
        expected += "Legal steps: ['update', 'create', 'export', 'delete']."
        self.assertEqual(result['args'][0], expected)

    # ERROR-HANDLERS------------------------------------------------------------
    def test_key_error_handler(self):
        result = self.client.post(
            '/api/workflow',
            json=json.dumps(dict(config={})),
        ).json
        self.assertEqual(result['error'], 'KeyError')

    def test_type_error_handler(self):
        result = self.client.post('/api/workflow', json=json.dumps([])).json
        self.assertEqual(result['error'], 'TypeError')

    def test_json_decode_error_handler(self):
        result = self.client.post('/api/workflow', json='bad json').json
        self.assertEqual(result['error'], 'JSONDecodeError')
