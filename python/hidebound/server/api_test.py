from pathlib import Path
import json
import os
import re

import numpy as np
# ------------------------------------------------------------------------------


# INITIALIZE--------------------------------------------------------------------
def test_initialize(env, extension, config, client):
    conf = dict(
        root_directory=config['root_directory'],
        hidebound_directory=config['hidebound_directory'],
        specification_files=config['specification_files'],
    )
    result = client.post('/api/initialize', json=json.dumps(conf))
    result = result.json['message']
    expected = 'Database initialized.'
    assert result == expected


def test_initialize_no_config(env, extension, config, client):
    result = client.post('/api/initialize').json['message']
    expected = 'Please supply a config dictionary.'
    assert re.search(expected, result) is not None


def test_initialize_bad_config_type(env, extension, config, client):
    bad_config = '["a", "b"]'
    result = client.post('/api/initialize', json=bad_config)
    result = result.json['message']
    expected = 'Please supply a config dictionary.'
    assert re.search(expected, result) is not None


def test_initialize_bad_config(env, extension, config, client):
    conf = dict(
        root_directory='/foo/bar',
        hidebound_directory=config['hidebound_directory'],
        specification_files=config['specification_files'],
    )
    result = client.post('/api/initialize', json=json.dumps(conf))
    result = result.json['message']
    expected = '/foo/bar is not a directory(.|\n)*or does not exist.'
    assert re.search(expected, result) is not None


# CREATE------------------------------------------------------------------------
def test_create(env, extension, config, client, make_files):
    client.post('/api/update')

    content = Path(config['hidebound_directory'], 'content')
    meta = Path(config['hidebound_directory'], 'metadata')
    assert os.path.exists(content) is False
    assert os.path.exists(meta) is False

    result = client.post('/api/create').json['message']
    expected = 'Hidebound data created.'
    assert result == expected
    assert os.path.exists(content)
    assert os.path.exists(meta)


def test_create_no_update(env, extension, client):
    result = client.post('/api/create').json['message']
    expected = 'Database not updated. Please call update.'
    assert re.search(expected, result) is not None


# READ--------------------------------------------------------------------------
def test_read(env, extension, client, make_files):
    client.post('/api/update')

    # call read
    result = client.post('/api/read', json={}).json['response']
    expected = extension.database.read()\
        .replace({np.nan: None})\
        .to_dict(orient='records')
    assert result == expected

    # test general exceptions
    extension.database = 'foo'
    result = client.post('/api/read', json={}).json['error']
    assert result == 'AttributeError'


def test_read_group_by_asset(env, extension, client, make_files):
    client.post('/api/update')

    # good params
    params = json.dumps({'group_by_asset': True})
    result = client.post('/api/read', json=params).json['response']
    expected = extension.database.read(group_by_asset=True)\
        .replace({np.nan: None})\
        .to_dict(orient='records')
    assert result == expected

    # bad params
    params = json.dumps({'foo': True})
    result = client.post('/api/read', json=params).json['message']
    expected = 'Please supply valid read params in the form '
    expected += r'\{"group_by_asset": BOOL\}\.'
    assert re.search(expected, result) is not None

    params = json.dumps({'group_by_asset': 'foo'})
    result = client.post('/api/read', json=params).json['message']
    expected = 'Please supply valid read params in the form '
    expected += r'\{"group_by_asset": BOOL\}\.'
    assert re.search(expected, result) is not None


def test_read_no_update(env, extension, client):
    result = client.post('/api/read', json={}).json['message']
    expected = 'Database not updated. Please call update.'
    assert re.search(expected, result) is not None


# UPDATE------------------------------------------------------------------------
def test_update(env, extension, client, make_files):
    result = client.post('/api/update').json['message']
    expected = 'Database updated.'
    assert result == expected


# DELETE------------------------------------------------------------------------
def test_delete(env, extension, client, config, make_files):
    client.post('/api/update')
    client.post('/api/create')

    content = Path(config['hidebound_directory'], 'content')
    meta = Path(config['hidebound_directory'], 'metadata')
    assert os.path.exists(content)
    assert os.path.exists(meta)

    result = client.post('/api/delete').json['message']
    expected = 'Hidebound data deleted.'
    assert result == expected
    assert os.path.exists(content) is False
    assert os.path.exists(meta) is False


def test_delete_no_create(env, extension, client, config, make_files):
    result = client.post('/api/delete').json['message']
    expected = 'Hidebound data deleted.'
    assert result == expected

    data = Path(config['hidebound_directory'], 'content')
    meta = Path(config['hidebound_directory'], 'metadata')
    assert os.path.exists(data) is False
    assert os.path.exists(meta) is False


# EXPORT------------------------------------------------------------------------
def test_export(env, extension, client, config, make_files):
    target_dir = config['exporters']['local_disk']['target_directory']
    result = os.listdir(target_dir)
    assert result == []

    client.post('/api/update')
    client.post('/api/create')
    client.post('/api/export')

    result = os.listdir(target_dir)
    assert 'content' in result
    assert 'metadata' in result


def test_export_error(env, extension, client, config, make_files):
    client.post('/api/update')
    result = client.post('/api/export').json['message']
    expected = 'hidebound/content directory does not exist'
    assert re.search(expected, result) is not None


# SEARCH------------------------------------------------------------------------
def test_search(env, extension, client, make_files):
    client.post('/api/update')

    # call search
    query = 'SELECT * FROM data WHERE specification == "spec001"'
    temp = {'query': query}
    temp = json.dumps(temp)
    result = client.post('/api/search', json=temp)
    result = result.json['response']
    expected = extension.database.search(query)\
        .replace({np.nan: None})\
        .to_dict(orient='records')
    assert result == expected


def test_search_group_by_asset(env, extension, client, make_files):
    client.post('/api/update')

    # call search
    query = 'SELECT * FROM data WHERE asset_type == "sequence"'
    temp = {'query': query, 'group_by_asset': True}
    temp = json.dumps(temp)
    result = client.post('/api/search', json=temp).json['response']
    expected = extension.database.search(query, group_by_asset=True)\
        .replace({np.nan: None})\
        .to_dict(orient='records')
    assert result == expected


def test_search_no_query(env, extension, client, make_files):
    result = client.post('/api/search', json={}).json['message']
    expected = 'Please supply valid search params in the form '
    expected += r'\{"query": SQL query, "group_by_asset": BOOL\}\.'
    assert re.search(expected, result) is not None


def test_search_bad_json(env, extension, client, make_files):
    query = {'foo': 'bar'}
    query = json.dumps(query)
    result = client.post('/api/search', json=query).json['message']
    expected = 'Please supply valid search params in the form '
    expected += r'\{"query": SQL query, "group_by_asset": BOOL\}\.'
    assert re.search(expected, result) is not None


def test_search_bad_group_by_asset(env, extension, client, make_files):
    params = dict(
        query='SELECT * FROM data WHERE asset_type == "sequence"',
        group_by_asset='foo'
    )
    params = json.dumps(params)
    result = client.post('/api/search', json=params).json['message']
    expected = 'Please supply valid search params in the form '
    expected += r'\{"query": SQL query, "group_by_asset": BOOL\}\.'
    assert re.search(expected, result) is not None


def test_search_bad_query(env, extension, client, make_files):
    client.post('/api/update', json={})
    query = {'query': 'SELECT * FROM data WHERE foo == "bar"'}
    query = json.dumps(query)
    result = client.post('/api/search', json=query).json['error']
    expected = 'PandaSQLException'
    assert result == expected


def test_search_no_update(env, extension, client, make_files):
    query = {'query': 'SELECT * FROM data WHERE specification == "spec001"'}
    query = json.dumps(query)
    result = client.post('/api/search', json=query).json['message']
    expected = 'Database not updated. Please call update.'
    assert re.search(expected, result) is not None


# WORKFLOW----------------------------------------------------------------------
def test_workflow(env, extension, client, config, make_files):
    expected = ['update', 'create', 'export', 'delete']

    data = dict(workflow=expected)
    data = json.dumps(data)
    result = client.post('/api/workflow', json=data).json

    assert result['message'] == 'Workflow completed.'
    assert result['workflow'] == expected

    data = Path(config['hidebound_directory'], 'content')
    assert os.path.exists(data) is False

    meta = Path(config['hidebound_directory'], 'metadata')
    assert os.path.exists(meta) is False


def test_workflow_create(env, extension, client, config, make_files):
    expected = ['update', 'create']

    data = dict(workflow=expected)
    data = json.dumps(data)
    result = client.post('/api/workflow', json=data).json

    assert result['message'] == 'Workflow completed.'
    assert result['workflow'] == expected

    data = Path(config['hidebound_directory'], 'content')
    assert os.path.exists(data)

    meta = Path(config['hidebound_directory'], 'metadata')
    assert os.path.exists(meta)


def test_workflow_bad_params(env, extension, client, make_files):
    workflow = json.dumps({})
    result = client.post('/api/workflow', json=workflow).json
    assert result['error'] == 'KeyError'


def test_workflow_illegal_step(env, extension, client, make_files):
    expected = ['update', 'create', 'foo', 'bar']
    data = dict(workflow=expected, config={})
    data = json.dumps(data)
    result = client.post('/api/workflow', json=data).json
    assert result['error'] == 'ValueError'

    expected = "Found illegal workflow steps: ['bar', 'foo']. "
    expected += "Legal steps: ['update', 'create', 'export', 'delete']."
    assert result['args'][0] == expected


# ERROR-HANDLERS----------------------------------------------------------------
def test_key_error_handler(env, extension, client, make_files):
    result = client.post(
        '/api/workflow',
        json=json.dumps(dict(config={})),
    ).json
    assert result['error'] == 'KeyError'


def test_type_error_handler(env, extension, client, make_files):
    result = client.post('/api/workflow', json=json.dumps([])).json
    assert result['error'] == 'TypeError'


def test_json_decode_error_handler(env, extension, client, make_files):
    result = client.post('/api/workflow', json='bad json').json
    assert result['error'] == 'JSONDecodeError'
