from pathlib import Path
import json
import os
import re
import time

import numpy as np
import pytest
# ------------------------------------------------------------------------------


RERUNS = 3
DELAY = 0.1


def try_post_json(
    client, url, json=None, status=None, attempts=10, delay=DELAY
):
    error = 'try_post_json failed.'
    response = None
    for _ in range(attempts):
        try:
            response = client.post(url, json=json)
        except Exception as error:  # noqa: F841
            error = error.args[0]
        time.sleep(delay)

        if status is not None and response.status_code != status:
            error = response.text
            continue
        return response.json

    raise RuntimeError(error)


# INITIALIZE--------------------------------------------------------------------
@pytest.mark.flaky(reruns=RERUNS)
def test_initialize(api_setup, flask_client, config):
    conf = dict(
        ingress_directory=config['ingress_directory'],
        staging_directory=config['staging_directory'],
        specification_files=config['specification_files'],
    )
    result = flask_client.post('/api/initialize', json=json.dumps(conf))
    result = result.json['message']
    expected = 'Database initialized.'
    assert result == expected


@pytest.mark.flaky(reruns=RERUNS)
def test_initialize_no_config(api_setup, flask_client, config):
    result = flask_client.post('/api/initialize').json['message']
    expected = 'Please supply a config dictionary.'
    assert re.search(expected, result) is not None


@pytest.mark.flaky(reruns=RERUNS)
def test_initialize_bad_config_type(api_setup, flask_client, config):
    bad_config = '["a", "b"]'
    result = flask_client.post('/api/initialize', json=bad_config)
    result = result.json['message']
    expected = 'Please supply a config dictionary.'
    assert re.search(expected, result) is not None


@pytest.mark.flaky(reruns=RERUNS)
def test_initialize_bad_config(api_setup, flask_client, config):
    conf = dict(
        ingress_directory='/foo/bar',
        staging_directory=config['staging_directory'],
        specification_files=config['specification_files'],
    )
    result = flask_client.post('/api/initialize', json=json.dumps(conf))
    result = result.json['message']
    expected = '/foo/bar is not a (.|\n)*directory or does not exist.'
    assert re.search(expected, result) is not None


# CREATE------------------------------------------------------------------------
@pytest.mark.flaky(reruns=RERUNS)
def test_create(api_setup, flask_client, config, make_files, api_update):
    content = Path(config['staging_directory'], 'content')
    meta = Path(config['staging_directory'], 'metadata')
    assert os.path.exists(content) is False
    assert os.path.exists(meta) is False

    result = try_post_json(flask_client, '/api/create')['message']
    expected = 'Hidebound data created.'
    assert result == expected
    assert os.path.exists(content)
    assert os.path.exists(meta)


@pytest.mark.flaky(reruns=RERUNS)
def test_create_no_update(api_setup, flask_client):
    result = flask_client.post('/api/create').json['message']
    time.sleep(DELAY)
    expected = 'Database not updated. Please call update.'
    assert re.search(expected, result) is not None


# READ--------------------------------------------------------------------------
@pytest.mark.flaky(reruns=RERUNS)
def test_read(api_setup, flask_client, make_files, api_update):
    extension = api_setup['extension']

    # call read
    result = try_post_json(
        flask_client, '/api/read', json={}, status=200
    )['response']
    expected = extension.database.read()\
        .replace({np.nan: None})\
        .to_dict(orient='records')
    assert result == expected

    # test general exceptions
    extension.database = 'foo'
    result = try_post_json(flask_client, '/api/read', json={})['error']
    assert result == 'AttributeError'


@pytest.mark.flaky(reruns=RERUNS)
def test_read_error(api_setup, flask_client):
    ext = api_setup['extension']
    db = ext.database
    ext.database = 'foo'
    result = flask_client.post('/api/read', json={}).json['error']
    assert result == 'AttributeError'
    ext.database = db


@pytest.mark.flaky(reruns=RERUNS)
def test_read_group_by_asset(api_setup, flask_client, make_files, api_update):
    extension = api_setup['extension']

    # good params
    params = json.dumps({'group_by_asset': True})
    result = flask_client.post('/api/read', json=params).json['response']
    expected = extension.database.read(group_by_asset=True)\
        .replace({np.nan: None})\
        .to_dict(orient='records')
    assert result == expected

    # bad params
    params = json.dumps({'foo': True})
    result = flask_client.post('/api/read', json=params).json['message']
    expected = 'Please supply valid read params in the form '
    expected += r'\{"group_by_asset": BOOL\}\.'
    assert re.search(expected, result) is not None

    params = json.dumps({'group_by_asset': 'foo'})
    result = flask_client.post('/api/read', json=params).json['message']
    expected = 'Please supply valid read params in the form '
    expected += r'\{"group_by_asset": BOOL\}\.'
    assert re.search(expected, result) is not None


@pytest.mark.flaky(reruns=RERUNS)
def test_read_no_update(api_setup, flask_client):
    result = flask_client.post('/api/read', json={}).json['message']
    expected = 'Database not updated. Please call update.'
    assert re.search(expected, result) is not None


# UPDATE------------------------------------------------------------------------
@pytest.mark.flaky(reruns=RERUNS)
def test_update(api_setup, flask_client, make_files):
    result = try_post_json(flask_client, '/api/update')['message']
    expected = 'Database updated.'
    assert result == expected


# DELETE------------------------------------------------------------------------
@pytest.mark.flaky(reruns=RERUNS)
def test_delete(api_setup, flask_client, config, make_files, api_update):
    flask_client.post('/api/create')
    time.sleep(DELAY)

    content = Path(config['staging_directory'], 'content')
    meta = Path(config['staging_directory'], 'metadata')
    assert os.path.exists(content)
    assert os.path.exists(meta)

    result = flask_client.post('/api/delete').json['message']
    expected = 'Hidebound data deleted.'
    assert result == expected
    assert os.path.exists(content) is False
    assert os.path.exists(meta) is False


@pytest.mark.flaky(reruns=RERUNS)
def test_delete_no_create(api_setup, flask_client, config, make_files):
    result = flask_client.post('/api/delete').json['message']
    expected = 'Hidebound data deleted.'
    assert result == expected

    data = Path(config['staging_directory'], 'content')
    meta = Path(config['staging_directory'], 'metadata')
    assert os.path.exists(data) is False
    assert os.path.exists(meta) is False


# EXPORT------------------------------------------------------------------------
@pytest.mark.flaky(reruns=RERUNS)
def test_export(api_setup, flask_client, config, make_files):
    target_dir = config['exporters'][0]['target_directory']
    result = os.listdir(target_dir)
    assert result == []

    try_post_json(flask_client, '/api/update')
    try_post_json(flask_client, '/api/create')
    try_post_json(flask_client, '/api/export')

    result = os.listdir(target_dir)
    assert 'content' in result
    assert 'metadata' in result


@pytest.mark.flaky(reruns=RERUNS)
def test_export_error(api_setup, flask_client, config, make_files, api_update):
    result = flask_client.post('/api/export').json['message']
    expected = 'hidebound/content directory does not exist'
    assert re.search(expected, result) is not None


# SEARCH------------------------------------------------------------------------
@pytest.mark.flaky(reruns=RERUNS)
def test_search(api_setup, flask_client, make_files, api_update):
    extension = api_setup['extension']

    # call search
    query = 'SELECT * FROM data WHERE specification == "spec001"'
    temp = {'query': query}
    temp = json.dumps(temp)
    result = try_post_json(flask_client, '/api/search', json=temp)['response']
    expected = extension.database.search(query)\
        .replace({np.nan: None})\
        .to_dict(orient='records')
    assert result == expected


@pytest.mark.flaky(reruns=RERUNS)
def test_search_group_by_asset(api_setup, flask_client, make_files, api_update):
    extension = api_setup['extension']

    # call search
    query = 'SELECT * FROM data WHERE asset_type == "sequence"'
    temp = {'query': query, 'group_by_asset': True}
    temp = json.dumps(temp)
    result = try_post_json(flask_client, '/api/search', json=temp)['response']
    expected = extension.database.search(query, group_by_asset=True)\
        .replace({np.nan: None})\
        .to_dict(orient='records')
    assert result == expected


@pytest.mark.flaky(reruns=RERUNS)
def test_search_no_query(api_setup, flask_client, make_files):
    result = flask_client.post('/api/search', json={}).json['message']
    expected = 'Please supply valid search params in the form '
    expected += r'\{"query": SQL query, "group_by_asset": BOOL\}\.'
    assert re.search(expected, result) is not None


@pytest.mark.flaky(reruns=RERUNS)
def test_search_bad_json(api_setup, flask_client, make_files):
    query = {'foo': 'bar'}
    query = json.dumps(query)
    result = flask_client.post('/api/search', json=query).json['message']
    expected = 'Please supply valid search params in the form '
    expected += r'\{"query": SQL query, "group_by_asset": BOOL\}\.'
    assert re.search(expected, result) is not None


@pytest.mark.flaky(reruns=RERUNS)
def test_search_bad_group_by_asset(api_setup, flask_client, make_files):
    params = dict(
        query='SELECT * FROM data WHERE asset_type == "sequence"',
        group_by_asset='foo'
    )
    params = json.dumps(params)
    result = flask_client.post('/api/search', json=params).json['message']
    expected = 'Please supply valid search params in the form '
    expected += r'\{"query": SQL query, "group_by_asset": BOOL\}\.'
    assert re.search(expected, result) is not None


@pytest.mark.flaky(reruns=RERUNS)
def test_search_bad_query(api_setup, flask_client, make_files):
    flask_client.post('/api/update', json={})
    query = {'query': 'SELECT * FROM data WHERE foo == "bar"'}
    query = json.dumps(query)
    result = flask_client.post('/api/search', json=query).json['error']
    expected = 'PandaSQLException'
    assert result == expected


@pytest.mark.flaky(reruns=RERUNS)
def test_search_no_update(api_setup, flask_client, make_files):
    query = {'query': 'SELECT * FROM data WHERE specification == "spec001"'}
    query = json.dumps(query)
    result = flask_client.post('/api/search', json=query).json['message']
    expected = 'Database not updated. Please call update.'
    assert re.search(expected, result) is not None


# WORKFLOW----------------------------------------------------------------------
@pytest.mark.flaky(reruns=RERUNS)
def test_workflow(api_setup, flask_client, config, make_files):
    expected = ['update', 'create', 'export', 'delete']

    data = dict(steps=expected)
    data = json.dumps(data)
    result = flask_client.post('/api/workflow', json=data).json

    assert result['message'] == 'Workflow completed.'
    assert result['steps'] == expected

    data = Path(config['staging_directory'], 'content')
    assert os.path.exists(data) is False

    meta = Path(config['staging_directory'], 'metadata')
    assert os.path.exists(meta) is False


@pytest.mark.flaky(reruns=RERUNS)
def test_workflow_create(api_setup, flask_client, config, make_files):
    expected = ['update', 'create']

    data = dict(steps=expected)
    data = json.dumps(data)
    result = flask_client.post('/api/workflow', json=data).json

    assert result['message'] == 'Workflow completed.'
    assert result['steps'] == expected

    data = Path(config['staging_directory'], 'content')
    assert os.path.exists(data)

    meta = Path(config['staging_directory'], 'metadata')
    assert os.path.exists(meta)


@pytest.mark.flaky(reruns=RERUNS)
def test_workflow_bad_params(api_setup, flask_client, make_files):
    workflow = json.dumps({})
    result = flask_client.post('/api/workflow', json=workflow).json
    assert result['error'] == 'KeyError'


@pytest.mark.flaky(reruns=RERUNS)
def test_workflow_illegal_step(api_setup, flask_client, make_files):
    expected = ['update', 'create', 'foo', 'bar']
    data = dict(steps=expected)
    data = json.dumps(data)
    result = flask_client.post('/api/workflow', json=data).json
    assert result['error'] == 'ValidationError'

    expected = r'bar.*foo.*are not legal workflow steps\. '
    expected += 'Legal steps: .*delete.*update.*create.*export'
    assert re.search(expected, result['args'][0]) is not None


# ERROR-HANDLERS----------------------------------------------------------------
@pytest.mark.flaky(reruns=RERUNS)
def test_key_error_handler(api_setup, flask_client, make_files):
    result = flask_client.post(
        '/api/workflow',
        json=json.dumps(dict()),
    ).json
    assert result['error'] == 'KeyError'


@pytest.mark.flaky(reruns=RERUNS)
def test_type_error_handler(api_setup, flask_client, make_files):
    result = flask_client.post('/api/workflow', json=json.dumps([])).json
    assert result['error'] == 'TypeError'


@pytest.mark.flaky(reruns=RERUNS)
def test_json_decode_error_handler(api_setup, flask_client, make_files):
    result = flask_client.post('/api/workflow', json='bad json').json
    assert result['error'] == 'JSONDecodeError'
