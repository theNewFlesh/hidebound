from copy import copy
from itertools import chain
from pathlib import Path
import json
import os
import re

from lunchbox.enforce import EnforceError
from moto import mock_s3
from schematics.exceptions import DataError
import boto3 as boto
import dask.distributed as ddist
import pytest
import yaml

from hidebound.core.database import Database, DaskConnection
from hidebound.exporters.mock_girder import MockGirderExporter
import hidebound.core.tools as hbt
# ------------------------------------------------------------------------------


DASK_WORKERS = 2
RERUNS = 3


# DASK-CONNECTION---------------------------------------------------------------
def test_dask_connection_init():
    result = DaskConnection('local', 9)
    assert result.cluster_type == 'local'
    assert result.num_workers == 9


def test_dask_connection_init_errors():
    with pytest.raises(EnforceError) as e:
        DaskConnection('foobar', 9)
    expected = 'Illegal cluster type: foobar. Legal cluster types:.*local'
    assert re.search(expected, str(e.value))

    with pytest.raises(EnforceError) as e:
        DaskConnection('local', 0)
    expected = 'num_workers must be greater than 0. Given value: 0.'
    assert re.search(expected, str(e.value))


def test_dask_connection_enter():
    with DaskConnection('local', 9) as result:
        assert isinstance(result, DaskConnection)
        assert isinstance(result.cluster, ddist.LocalCluster)
        assert len(result.cluster.workers) == 9
        assert result.cluster.status.name == 'running'


def test_dask_connection_exit():
    with DaskConnection('local', 9) as result:
        pass
    assert result.cluster.status.name == 'closed'


# DATABASE----------------------------------------------------------------------
def test_from_config(make_dirs, spec_file):  # noqa: F811
    ingress, staging, _ = make_dirs
    config = dict(
        ingress_directory=ingress,
        staging_directory=staging,
        specification_files=[spec_file],
        include_regex='foo',
        exclude_regex='bar',
        write_mode='copy',
        dask_workers=DASK_WORKERS,
        testing=False,
    )
    expected = copy(config)
    Database.from_config(config)
    assert config == expected

    config['specification_files'] = ['/foo/bar.py']
    with pytest.raises(DataError):
        Database.from_config(config)


def test_from_json(temp_dir, make_dirs, spec_file):  # noqa: F811
    ingress, staging, _ = make_dirs

    config = dict(
        ingress_directory=ingress,
        staging_directory=staging,
        specification_files=[spec_file],
        include_regex='foo',
        exclude_regex='bar',
        write_mode='copy',
        dask_workers=DASK_WORKERS,
        testing=False,
    )
    config_file = Path(temp_dir, 'config.json')
    with open(config_file, 'w') as f:
        json.dump(config, f)

    Database.from_json(config_file)


def test_from_yaml(temp_dir, make_dirs, spec_file):  # noqa: F811
    ingress, staging, _ = make_dirs

    config = dict(
        ingress_directory=ingress,
        staging_directory=staging,
        specification_files=[spec_file],
        include_regex='foo',
        exclude_regex='bar',
        write_mode='copy',
        dask_workers=DASK_WORKERS,
        testing=False,
    )
    config_file = Path(temp_dir, 'config.yaml')
    with open(config_file, 'w') as f:
        yaml.safe_dump(config, f)

    Database.from_yaml(config_file)


def test_init(make_dirs, make_files, specs):  # noqa: F811
    ingress, staging, _ = make_dirs
    Spec001, Spec002, _ = specs
    Database(
        ingress, staging, dask_workers=DASK_WORKERS, testing=False
    )
    Database(
        ingress, staging, [Spec001], dask_workers=DASK_WORKERS, testing=False
    )
    Database(
        ingress, staging, [Spec001, Spec002], dask_workers=DASK_WORKERS,
        testing=False
    )


def test_init_bad_ingress(make_dirs, specs):  # noqa: F811
    _, staging, _ = make_dirs
    Spec001, _, _ = specs
    expected = '/foo is not a directory or does not exist'
    with pytest.raises(FileNotFoundError) as e:
        Database(
            '/foo', staging, [Spec001], dask_workers=DASK_WORKERS,
            testing=False
        )
        assert re.search(expected, str(e))


def test_init_bad_staging(temp_dir):  # noqa: F811
    staging = Path(temp_dir, 'hidebound')

    expected = '/hidebound is not a directory or does not exist'
    with pytest.raises(FileNotFoundError) as e:
        Database(temp_dir, staging, dask_workers=DASK_WORKERS, testing=False)
        assert re.search(expected, str(e))

    temp = Path(temp_dir, 'Hidebound')
    os.makedirs(temp)
    expected = r'Hidebound directory is not named hidebound\.$'
    with pytest.raises(NameError) as e:
        Database(temp_dir, temp, dask_workers=DASK_WORKERS, testing=False)
        assert re.search(expected, str(e))


def test_init_bad_specifications(make_dirs, make_files, specs):  # noqa: F811
    Spec001, _, BadSpec = specs
    ingress, staging, _ = make_dirs

    expected = 'SpecificationBase may only contain subclasses of'
    expected += ' SpecificationBase. Found: .*.'

    with pytest.raises(TypeError) as e:
        Database(
            ingress, staging, [BadSpec], dask_workers=DASK_WORKERS,
            testing=False
        )
        assert re.search(str(e), expected)

    with pytest.raises(TypeError) as e:
        Database(
            ingress, staging, [Spec001, BadSpec], dask_workers=DASK_WORKERS,
            testing=False
        )
        assert re.search(str(e), expected)


def test_init_bad_write_mode(make_dirs, specs):  # noqa: F811
    Spec001, _, _ = specs
    ingress, staging, _ = make_dirs

    expected = r"Invalid write mode: foo not in \['copy', 'move'\]\."
    with pytest.raises(ValueError) as e:
        Database(
            ingress,
            staging,
            [Spec001],
            write_mode='foo',
            dask_workers=DASK_WORKERS,
            testing=False,
        )
        assert re.search(str(e), expected)


def test_init_testing(make_dirs):
    ingress, staging, _ = make_dirs
    result = Database(ingress, staging, dask_workers=DASK_WORKERS, testing=False)
    assert result._testing is False

    result = Database(ingress, staging, dask_workers=DASK_WORKERS, testing=True)
    assert result._testing is True


# CREATE------------------------------------------------------------------------
@pytest.mark.flaky(rerun=3)
def test_create(make_dirs, make_files, specs):  # noqa: F811
    Spec001, Spec002, _ = specs
    ingress, staging, _ = make_dirs

    db = Database(
        ingress, staging, [Spec001, Spec002], dask_workers=DASK_WORKERS,
        testing=False
    )
    db.update()
    data = db.data
    db.create()
    data = data[data.asset_valid]

    # ensure files are written
    result = Path(staging, 'content')
    result = hbt.directory_to_dataframe(result)
    result = sorted(result.filename.tolist())
    assert len(result) > 0
    expected = sorted(data.filename.tolist())
    assert result == expected

    # ensure file metadata is written
    result = len(os.listdir(Path(staging, 'metadata', 'file')))
    assert result > 0
    expected = data.filepath.nunique()
    assert result == expected

    # ensure asset metadata is written
    result = len(os.listdir(Path(staging, 'metadata', 'asset')))
    assert result > 0
    expected = data.asset_path.nunique()
    assert result == expected

    # ensure asset chunk is written
    result = len(os.listdir(Path(staging, 'metadata', 'asset-chunk')))
    assert result == 1

    # ensure file chunk is written
    result = len(os.listdir(Path(staging, 'metadata', 'file-chunk')))
    assert result == 1


def test_create_no_init(make_dirs, make_files, specs):  # noqa: F811
    Spec001, Spec002, _ = specs
    ingress, staging, _ = make_dirs

    db = Database(
        ingress, staging, [Spec001, Spec002], dask_workers=DASK_WORKERS,
        testing=False
    )
    expected = 'Data not initialized. Please call update.'
    with pytest.raises(RuntimeError) as e:
        db.create()
        assert re.search(str(e), expected)


def test_create_all_invalid(make_dirs, make_files, specs):  # noqa: F811
    Spec001, Spec002, _ = specs
    ingress, staging, _ = make_dirs

    db = Database(
        ingress, staging, [Spec001, Spec002], dask_workers=DASK_WORKERS,
        testing=False
    )
    db.update()
    data = db.data
    data['asset_valid'] = False
    db.create()

    result = Path(staging, 'content')
    assert result.exists() is False

    result = Path(staging, 'metadata', 'file')
    assert result.exists() is False

    result = Path(staging, 'metadata', 'asset')
    assert result.exists() is False


def test_create_copy(make_dirs, make_files, specs):  # noqa: F811
    Spec001, Spec002, _ = specs
    ingress, staging, _ = make_dirs

    db = Database(
        ingress,
        staging,
        [Spec001, Spec002],
        write_mode='copy',
        dask_workers=DASK_WORKERS,
        testing=False,
    )
    db.update()
    db.create()

    result = hbt.directory_to_dataframe(ingress).filepath.tolist()
    result = sorted(result)
    assert result == make_files


def test_create_move(make_dirs, make_files, specs):  # noqa: F811
    Spec001, Spec002, _ = specs
    ingress, staging, _ = make_dirs

    db = Database(
        ingress,
        staging,
        [Spec001, Spec002],
        write_mode='move',
        dask_workers=DASK_WORKERS,
        testing=False,
    )
    db.update()
    data = db.data
    db.create()
    data = data[data.asset_valid]

    # assert that no valid asset files are found in their original
    result = data.filepath.apply(lambda x: os.path.exists(x)).unique().tolist()
    assert result == [False]

    # ensure files are written
    result = Path(staging, 'content')
    result = hbt.directory_to_dataframe(result)
    result = sorted(result.filename.tolist())
    assert len(result) > 0
    expected = sorted(data.filename.tolist())
    assert result == expected

    # ensure file metadata is written
    result = len(os.listdir(Path(staging, 'metadata', 'file')))
    assert result > 0
    expected = data.filepath.nunique()
    assert result == expected

    # ensure asset metadata is written
    result = len(os.listdir(Path(staging, 'metadata', 'asset')))
    assert result > 0
    expected = data.asset_path.nunique()
    assert result == expected


# READ--------------------------------------------------------------------------
@pytest.mark.flaky(reruns=RERUNS)
def test_read_legal_types(make_dirs, make_files, specs):  # noqa: F811
    Spec001, Spec002, _ = specs
    ingress, staging, _ = make_dirs

    db = Database(
        ingress, staging, [Spec001, Spec002], dask_workers=DASK_WORKERS,
        testing=False
    )

    # test data initiliazation error
    expected = 'Data not initialized. Please call update.'
    with pytest.raises(RuntimeError) as e:
        db.read()
        assert re.search(expected, str(e))

    db.update()
    data = db.read()

    # test types by file
    result = data.applymap(type)\
        .apply(lambda x: x.unique().tolist())\
        .tolist()
    result = list(chain(*result))
    result = set(result)

    expected = set([int, float, str, bool, None])
    result = result.difference(expected)
    assert len(result) == 0

    # test types by asset
    data = db.read(group_by_asset=True)
    result = data.applymap(type)\
        .apply(lambda x: x.unique().tolist()) \
        .loc[0].tolist()
    result = set(result)

    expected = set([int, float, str, bool, None])
    result = result.difference(expected)
    assert len(result) == 0


def test_read_traits(make_dirs, make_files, specs):  # noqa: F811
    Spec001, Spec002, _ = specs
    ingress, staging, _ = make_dirs
    db = Database(
        ingress, staging, [Spec001, Spec002], dask_workers=DASK_WORKERS,
        testing=False
    )
    db.update()

    # test file traits
    db.data.file_traits = db.data.file_traits\
        .apply(lambda x: {'foo': 'bar', 'illegal': set()})
    data = db.read()

    result = data.columns
    assert 'foo' in result
    assert 'illegal' not in result

    # test asset traits
    db.update()

    db.data.asset_traits = db.data.asset_traits\
        .apply(lambda x: {'foo': 'bar', 'illegal': set()})
    data = db.read(group_by_asset=True)

    result = data.columns
    assert 'foo' in result
    assert 'illegal' not in result


def test_read_coordinates(make_dirs, make_files, specs):  # noqa: F811
    Spec001, Spec002, _ = specs
    ingress, staging, _ = make_dirs

    db = Database(
        ingress, staging, [Spec001, Spec002], dask_workers=DASK_WORKERS,
        testing=False
    )
    db.update()

    db.data.file_traits = db.data.file_traits\
        .apply(lambda x: {'coordinate': [0, 1]})
    data = db.read()

    # xy
    result = data.columns
    expected = ['coordinate_x', 'coordinate_y']
    for col in expected:
        assert col in result
    assert 'coordinate_z' not in result

    # xyz
    db.update()

    db.data.file_traits = db.data.file_traits\
        .apply(lambda x: {'coordinate': [0, 1, 0]})
    data = db.read()

    result = data.columns
    expected = ['coordinate_x', 'coordinate_y', 'coordinate_z']
    for col in expected:
        assert col in result


@pytest.mark.flaky(reruns=RERUNS)
def test_read_column_order(make_dirs, make_files, specs):  # noqa: F811
    Spec001, Spec002, _ = specs
    ingress, staging, _ = make_dirs
    db = Database(
        ingress, staging, [Spec001, Spec002], dask_workers=DASK_WORKERS,
        testing=False
    )
    db.update()

    result = db.read()
    result = result.columns.tolist()
    expected = [
        'project',
        'specification',
        'descriptor',
        'version',
        'coordinate_x',
        'coordinate_y',
        'coordinate_z',
        'frame',
        'extension',
        'filename',
        'filepath',
        'file_error',
        'asset_name',
        'asset_path',
        'asset_type',
        'asset_error',
        'asset_valid',
    ]
    expected = list(filter(lambda x: x in result, expected))
    result = result[:len(expected)]
    assert result == expected


def test_read_no_files(make_dirs, specs):  # noqa: F811
    Spec001, Spec002, _ = specs
    ingress, staging, _ = make_dirs

    db = Database(
        ingress, staging, [Spec001, Spec002], dask_workers=DASK_WORKERS,
        testing=False
    )

    db.update()
    result = db.read()
    assert len(result) == 0


# UPDATE------------------------------------------------------------------------
def test_update(make_dirs, make_files, specs):  # noqa: F811
    Spec001, Spec002, _ = specs
    ingress, staging, _ = make_dirs

    data = Database(
        ingress, staging, [Spec001, Spec002], dask_workers=DASK_WORKERS,
        testing=False
    )
    data = data.update().data
    result = data.filepath.tolist()
    result = list(filter(lambda x: 'progress' not in x, result))
    result = sorted(result)
    assert result == make_files

    result = data.groupby('asset_path').asset_valid.first().tolist()
    expected = [True, True, False, True, False]
    assert result == expected


def test_update_exclude(make_dirs, make_files, specs):  # noqa: F811
    Spec001, Spec002, _ = specs
    ingress, staging, _ = make_dirs

    regex = r'misc\.txt|vdb'
    expected = list(filter(lambda x: not re.search(regex, x), make_files))
    expected = sorted(expected)

    result = Database(
        ingress,
        staging,
        [Spec001, Spec002],
        exclude_regex=regex,
        dask_workers=DASK_WORKERS,
        testing=False,
    )
    result = result.update().data.filepath.tolist()
    result = list(filter(lambda x: 'progress' not in x, result))
    result = sorted(result)
    assert result == expected


def test_update_include(make_dirs, make_files, specs):  # noqa: F811
    Spec001, Spec002, _ = specs
    ingress, staging, _ = make_dirs

    regex = r'misc\.txt|vdb'
    expected = list(filter(lambda x: re.search(regex, x), make_files))
    expected = sorted(expected)

    result = Database(
        ingress,
        staging,
        [Spec001, Spec002],
        include_regex=regex,
        dask_workers=DASK_WORKERS,
        testing=False,
    )
    result = result.update().data.filepath.tolist()
    result = sorted(result)
    assert result == expected


def test_update_include_exclude(make_dirs, make_files, specs):  # noqa: F811
    Spec001, Spec002, _ = specs
    ingress, staging, _ = make_dirs

    i_regex = r'pizza'
    expected = list(filter(lambda x: re.search(i_regex, x), make_files))
    e_regex = r'misc\.txt|vdb'
    expected = list(filter(lambda x: not re.search(e_regex, x), expected))
    expected = sorted(expected)

    result = Database(
        ingress,
        staging,
        [Spec001, Spec002],
        include_regex=i_regex,
        exclude_regex=e_regex,
        dask_workers=DASK_WORKERS,
        testing=False,
    )
    result = result.update().data.filepath.tolist()
    result = sorted(result)
    assert result == expected


def test_update_no_files(make_dirs, specs, db_columns):  # noqa: F811
    Spec001, _, _ = specs
    ingress, staging, _ = make_dirs

    result = Database(
        ingress, staging, [Spec001], dask_workers=DASK_WORKERS, testing=False
    )
    result = result.update().data
    assert len(result) == 0
    assert result.columns.tolist() == db_columns


def test_update_error(make_dirs, make_files, specs, db_data):  # noqa: F811
    Spec001, Spec002, _ = specs
    ingress, staging, _ = make_dirs

    data = Database(
        ingress, staging, [Spec001, Spec002], dask_workers=DASK_WORKERS,
        testing=False
    )
    data = data.update().data
    keys = db_data.filepath.tolist()
    lut = dict(zip(keys, db_data.file_error.tolist()))
    data = data[data.filepath.apply(lambda x: x in keys)]

    regexes = data.filepath.apply(lambda x: lut[x.as_posix()]).tolist()
    results = data.file_error.apply(lambda x: x[0]).tolist()
    for result, regex in zip(results, regexes):
        assert re.search(regex, result)


# DELETE------------------------------------------------------------------------
def test_delete(make_dirs, make_files, specs):  # noqa: F811
    ingress, staging, _ = make_dirs

    data_dir = Path(staging, 'content')
    meta_dir = Path(staging, 'metadata')

    expected = hbt.directory_to_dataframe(ingress).filepath.tolist()
    expected = sorted(expected)

    db = Database(
        ingress, staging, [], dask_workers=DASK_WORKERS, testing=False
    )
    db.delete()

    assert data_dir.exists() is False
    assert meta_dir.exists() is False

    result = hbt.directory_to_dataframe(ingress).filepath.tolist()
    result = sorted(result)
    assert result == expected


# EXPORT------------------------------------------------------------------------
@pytest.mark.flaky(reruns=RERUNS)
def test_export_girder(make_dirs, make_files, specs):  # noqa: F811
    Spec001, Spec002, _ = specs
    ingress, staging, _ = make_dirs

    exporters = [dict(name='girder', api_key='api_key', root_id='root_id')]
    db = Database(
        ingress,
        staging,
        [Spec001, Spec002],
        exporters=exporters,
        dask_workers=DASK_WORKERS,
        testing=False,
    )
    db._Database__exporter_lut = dict(girder=MockGirderExporter)

    db.update().create().export()

    db_client = db._Database__exporter_lut['girder']._client
    result = list(db_client.folders.keys())
    asset_paths = [
        'p-proj001_s-spec001_d-pizza_v001',
        'p-proj001_s-spec001_d-pizza_v002',
        'p-proj001_s-spec002_d-taco_v001',
    ]
    for expected in asset_paths:
        assert expected in result


@mock_s3
def test_export_s3(make_dirs, make_files, specs, db_data):  # noqa: F811
    Spec001, Spec002, _ = specs
    ingress, staging, _ = make_dirs

    exporters = [dict(
        name='s3',
        access_key='foo',
        secret_key='bar',
        bucket='bucket',
        region='us-west-2',
    )]
    db = Database(
        ingress,
        staging,
        [Spec001, Spec002],
        exporters=exporters,
        dask_workers=DASK_WORKERS,
        testing=False,
    )

    db.update().create().export()

    results = boto.session \
        .Session(
            aws_access_key_id='foo',
            aws_secret_access_key='bar',
            region_name='us-west-2',
        ) \
        .resource('s3') \
        .Bucket('bucket') \
        .objects.all()
    results = [x.key for x in results]

    # content
    data = db_data
    data = data[data.asset_valid]
    expected = data.filepath.apply(lambda x: Path(*x.parts[4:])).tolist()
    expected = sorted([f'hidebound/content/{x}' for x in expected])
    content = sorted(list(filter(lambda x: re.search('content', x), results)))
    assert content == expected

    # asset metadata
    expected = data.asset_path.nunique()
    result = len(list(filter(
        lambda x: re.search('metadata/asset/', x), results
    )))
    assert result == expected

    # file metadata
    result = len(list(filter(
        lambda x: re.search('metadata/file/', x), results
    )))
    assert result == len(content)

    # asset chunk
    result = len(list(filter(
        lambda x: re.search('metadata/asset-chunk/', x), results
    )))
    assert result == 1

    # file chunk
    result = len(list(filter(
        lambda x: re.search('metadata/file-chunk/', x), results
    )))
    assert result == 1


def test_export_disk(make_dirs, make_files, specs, db_data):  # noqa: F811
    Spec001, Spec002, _ = specs
    ingress, staging, archive = make_dirs

    exporters = [dict(name='disk', target_directory=archive)]
    db = Database(
        ingress,
        staging,
        [Spec001, Spec002],
        exporters=exporters,
        dask_workers=DASK_WORKERS,
        testing=False,
    )

    db.update()
    db.create()
    assert len(os.listdir(archive)) == 0
    db.export()

    expected = hbt.directory_to_dataframe(staging).filepath
    mask = expected \
        .apply(lambda x: re.search('/(asset|file|content)', x)) \
        .astype(bool)
    expected = expected[mask] \
        .apply(lambda x: re.sub('.*/hidebound/', '', x)) \
        .tolist()
    expected = sorted(expected)

    result = hbt.directory_to_dataframe(archive).filepath \
        .apply(lambda x: re.sub('.*/archive/', '', x)) \
        .tolist()
    result = sorted(result)

    # time string in metadata chunk files screws up tests
    regex = re.compile(r'(.*-chunk.*)(\d\d\d\d-\d\d-\d\d).*.json')
    result = [regex.sub('\\1\\2.json', x) for x in result]
    expected = [regex.sub('\\1\\2.json', x) for x in expected]

    assert result == expected


# SEARCH------------------------------------------------------------------------
@pytest.mark.flaky(reruns=RERUNS)
def test_search(make_dirs, make_files, specs):  # noqa: F811
    Spec001, Spec002, _ = specs
    ingress, staging, _ = make_dirs

    db = Database(
        ingress, staging, [Spec001, Spec002], dask_workers=DASK_WORKERS,
        testing=False
    )
    db.update()
    db.search('SELECT * FROM data WHERE version == 1')


# WEBHOOKS----------------------------------------------------------------------
def test_call_webhooks(make_dirs, make_files, spec_file):  # noqa: F811
    ingress, staging, _ = make_dirs

    config = dict(
        ingress_directory=ingress,
        staging_directory=staging,
        specification_files=[spec_file],
        include_regex='foo',
        exclude_regex='bar',
        write_mode='copy',
        dask_workers=DASK_WORKERS,
        testing=False,
        webhooks=[
            {
                'url': 'http://foobar.com/api/user?',
                'method': 'get',
                'headers': {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                'timeout': 10,
                'params': {
                    'foo': 'bar'
                }
            },
            {
                'url': 'http://foobar.com/api/user?',
                'method': 'post',
                'headers': {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                'data': {
                    'id': '123',
                    'name': 'john',
                    'other': {'stuff': 'things'}
                },
                'json': {
                    'foo': 'bar'
                }
            }
        ]
    )

    db = Database.from_config(config)
    for response in db.call_webhooks():
        assert response.status_code == 403
