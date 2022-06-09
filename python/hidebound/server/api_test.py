import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import flasgger as swg
import flask
import lunchbox.tools as lbt
import numpy as np
import yaml

from hidebound.core.database import Database
from hidebound.core.database_test_base import DatabaseTestBase
from hidebound.server.api import ApiExtension
# ------------------------------------------------------------------------------


class ApiExtensionTestBase(DatabaseTestBase):
    def setUp(self):
        # setup files and dirs
        self.temp_dir = TemporaryDirectory()
        self.config = self.get_config(self.temp_dir.name)
        self.root = self.config['root_directory']
        self.hb_root = self.config['hidebound_directory']
        self.target_dir = self.config['exporters']['local_disk']['target_directory']
        self.create_files(self.root)

        # setup app
        app = flask.Flask(__name__)
        self.context = app.app_context()
        self.context.push()
        self.app = self.context.app
        self.app.config['TESTING'] = True

        # set instance members
        self.client = self.app.test_client()
        self.specs = lbt.relative_path(
            __file__, '../core/test_specifications.py'
        ).absolute().as_posix()

    def tearDown(self):
        self.context.pop()
        self.temp_dir.cleanup()

        # remove HIDEBOUND_XXX env vars
        keys = filter(lambda x: x.startswith('HIDEBOUND_'), os.environ.keys())
        list(map(os.environ.pop, keys))

    def setup_api(self):
        swg.Swagger(self.app)
        self.api = ApiExtension(self.app)
        self.api.connect()

    def get_config(self, temp_dir):
        ingress = Path(temp_dir, 'ingress').as_posix()
        hidebound = Path(temp_dir, 'hidebound').as_posix()
        archive = Path(temp_dir, 'archive').as_posix()

        # creates dirs
        os.makedirs(ingress)
        os.makedirs(hidebound)
        os.makedirs(archive)

        config = dict(
            root_directory=ingress,
            hidebound_directory=hidebound,
            include_regex='',
            exclude_regex=r'\.DS_Store',
            write_mode='copy',
            dask_enabled=False,
            dask_workers=3,
        )
        extra = dict(
            specification_files=[
                '/home/ubuntu/hidebound/python/hidebound/core/test_specifications.py'
            ],
            exporters=dict(
                local_disk=dict(
                    target_directory=archive,
                    metadata_types=['asset', 'file', 'asset-chunk', 'file-chunk']
                )
            ),
            webhooks=[
                dict(
                    url='http://foobar.com/api/user?',
                    method='get',
                    params={'id': 123},
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                    }
                )
            ]
        )

        for key, val in config.items():
            os.environ[f'HIDEBOUND_{key.upper()}'] = str(val)
        for key, val in extra.items():
            os.environ[f'HIDEBOUND_{key.upper()}'] = yaml.safe_dump(val)

        config.update(extra)
        return config

    def write_config(self, config, temp_dir):
        filepath = None
        filepath = Path(temp_dir, 'hidebound_config.yaml').as_posix()
        with open(filepath, 'w') as f:
            yaml.safe_dump(config, f)

        os.environ['HIDEBOUND_CONFIG_FILEPATH'] = filepath
        return filepath
# ------------------------------------------------------------------------------


class ApiExtensionInitTests(ApiExtensionTestBase):
    def test_init(self):
        result = ApiExtension(app=None)
        self.assertIsNone(result.app)
        self.assertIsNone(result.config)
        self.assertIsNone(result.database)

        result = ApiExtension(app=self.app)
        self.assertIs(result.app, self.app)
        self.assertIs(result.app.api, result)
        self.assertIsNone(result.config)
        self.assertIsNone(result.database)

    def test_get_config_from_env(self):
        with TemporaryDirectory() as root:
            expected = self.get_config(root)
            self.app.config.from_prefixed_env('HIDEBOUND')
            result = ApiExtension()._get_config_from_env(self.app)
            for key, val in expected.items():
                self.assertEqual(result[key], val)

    def test_get_config_from_file(self):
        with TemporaryDirectory() as root:
            expected = self.get_config(root)
            filepath = self.write_config(expected, root)
            result = ApiExtension()._get_config_from_file(filepath)
            for key, val in expected.items():
                self.assertEqual(result[key], val)

    def test_get_config_from_file_error(self):
        expected = 'Hidebound config files must end in one of these extensions:'
        expected += r" \['json', 'yml', 'yaml'\]\. Given file: "
        expected += r'/foo/bar/config\.pizza\.'
        with self.assertRaisesRegexp(FileNotFoundError, expected):
            ApiExtension()._get_config_from_file('/foo/bar/config.pizza')

    def test_get_config_env_vars(self):
        with TemporaryDirectory() as root:
            expected = self.get_config(root)
            self.app.config.from_prefixed_env('HIDEBOUND')
            result = ApiExtension()._get_config(self.app)
            for key, val in expected.items():
                self.assertEqual(result[key], val)

    def test_get_config_filepath(self):
        with TemporaryDirectory() as root:
            expected = self.get_config(root)
            expected['write_mode'] = 'move'
            self.write_config(expected, root)
            self.app.config.from_prefixed_env('HIDEBOUND')
            result = ApiExtension()._get_config(self.app)
            for key, val in expected.items():
                self.assertEqual(result[key], val)

    def test_init_app(self):
        api = ApiExtension()
        api.init_app(self.app)

        # endpoints
        result = [x.rule for x in self.app.url_map.iter_rules()]
        self.assertIn('/api', result)
        self.assertIn('/api/create', result)
        self.assertIn('/api/delete', result)
        self.assertIn('/api/export', result)
        self.assertIn('/api/initialize', result)
        self.assertIn('/api/read', result)
        self.assertIn('/api/search', result)
        self.assertIn('/api/update', result)
        self.assertIn('/api/workflow', result)

        # error handlers
        result = self.app.error_handler_spec[None][None].values()
        result = [x.__name__ for x in result]
        self.assertIn('handle_data_error', result)
        self.assertIn('handle_key_error', result)
        self.assertIn('handle_type_error', result)
        self.assertIn('handle_json_decode_error', result)

        # instance binding
        self.assertIs(api.app, self.app)
        self.assertIs(self.app.api, api)

    def test_connect(self):
        with TemporaryDirectory() as root:
            expected = self.get_config(root)
            result = ApiExtension(app=self.app)
            result.connect()
            self.assertEqual(result.config, expected)
            self.assertIsInstance(result.database, Database)

    def test_disconnect(self):
        with TemporaryDirectory() as root:
            self.get_config(root)
            result = ApiExtension(app=self.app)
            result.connect()
            result.disconnect()
            self.assertIsNone(result.config)
            self.assertIsNone(result.database)
# ------------------------------------------------------------------------------


class ApiExtensionEndpointTests(ApiExtensionTestBase):
    def setUp(self):
        super().setUp()
        self.setup_api()

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
