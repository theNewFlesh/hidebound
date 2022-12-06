from copy import deepcopy
from pathlib import Path
import json
import re

from pandas import DataFrame
import dask.dataframe as dd
import lunchbox.tools as lbt
import numpy as np
import pandas as pd

from hidebound.core.specification_base import ComplexSpecificationBase
from hidebound.core.specification_base import FileSpecificationBase
from hidebound.core.specification_base import SequenceSpecificationBase
import hidebound.core.database_tools as db_tools

ENABLE_DASK_CLUSTER = True
NUM_PARTITIONS = 2
# ------------------------------------------------------------------------------


class Spec001(FileSpecificationBase):
    name = 'spec001'
    filename_fields = ['specification']


class Spec002(SequenceSpecificationBase):
    name = 'spec002'
    filename_fields = ['specification']


class Spec003(ComplexSpecificationBase):
    name = 'spec003'
    filename_fields = ['specification']


# SPECIFICATION-FUNCTIONS-------------------------------------------------------
def test_add_specification(db_cluster, dir_data):
    specs = {Spec001.name: Spec001, Spec002.name: Spec002}
    data = dir_data

    expected = data.copy().compute()
    expected['specification'] = expected.filename.apply(
        lambda x: lbt.try_(
            lambda y: re.search(r's-([a-z]+\d\d\d)_d', y).group(1), x, np.nan,
        )
    )
    expected['specification_class'] = expected.specification.apply(
        lambda x: lbt.try_(lambda y: specs[y], x, np.nan)
    )

    result = db_tools.add_specification(data, specs).compute()

    r = result.specification.fillna('null').tolist()
    e = expected.specification.fillna('null').tolist()
    assert r == e

    r = result.specification_class.fillna('null').tolist()
    e = expected.specification_class.fillna('null').tolist()
    assert r == e

    mask = result.filename.apply(lambda x: 'misc.txt' in x)
    expected = result[mask].file_error.values[0]
    assert re.search(
        'Specification not found in "misc.txt"',
        expected,
    ) is not None

    assert pd.isnull(result.loc[0, 'file_error']) is True


# FILE-FUNCTIONS----------------------------------------------------------------
def test_validate_filepath(db_cluster, db_data_nans):
    data = db_data_nans

    error = 'Invalid asset directory name'
    mask = data.file_error == error
    data.loc[mask, 'file_error'] = np.nan

    cols = ['specification_class', 'filepath', 'file_error']
    data = data[cols]

    data = dd.from_pandas(data, npartitions=NUM_PARTITIONS)
    data = db_tools.validate_filepath(data).compute()
    result = data.loc[mask, 'file_error'].tolist()[0]
    assert re.search(error, result) is not None


def test_add_file_traits(db_cluster, specs):
    Spec001, Spec002, _ = specs
    data = [
        [
            Spec001,
            '/tmp/p-proj001_s-spec001_d-desc_v001_c0000-0000_f0001.png',
            np.nan,
            'proj001', 'spec001', 'desc', 1, [0, 0], 1, 'png'
        ],
        [
            Spec001,
            '/tmp/p-proj001_s-spec001_d-desc_v001_c0000-0000_f0002.png',
            np.nan,
            'proj001', 'spec001', 'desc', 1, [0, 0], 2, 'png'
        ],
        [
            Spec002,
            '/tmp/p-proj002_s-spec002_d-MASTER_v001_f0001.png',
            'file_Error',
            np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan
        ],
        [
            Spec002,
            '/tmp/p-proj002_s-spec002_d-desc_v001_f0002.png',
            np.nan,
            'proj002', 'spec002', 'desc', 1, np.nan, 2, 'png'
        ],
        [
            np.nan,
            '/tmp/misc.txt',
            'file_Error',
            np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan
        ],
    ]
    data = DataFrame(data)
    cols = [
        'project', 'specification', 'descriptor', 'version', 'coordinate',
        'frame', 'extension'
    ]
    data.columns = ['specification_class', 'filepath', 'file_error'] + cols
    temp = data.copy()
    data = dd.from_pandas(data, npartitions=NUM_PARTITIONS)

    data = db_tools.add_file_traits(data).compute()
    for col in cols:
        result = data[col].fillna('null').tolist()
        expected = temp[col].fillna('null').tolist()
        assert result == expected


# ASSET-FUNCTIONS---------------------------------------------------------------
def test_add_asset_traits(db_cluster):
    data = DataFrame()
    data['asset_path'] = ['a', 'a', 'b', 'b', np.nan]
    data['file_traits'] = [
        dict(w=0, x=1, y=1),
        dict(x=2, y=2),
        dict(x=1, y=1, z=1),
        dict(x=2, y=2, z=2),
        {},
    ]
    data = dd.from_pandas(data, npartitions=NUM_PARTITIONS)

    result = db_tools.add_asset_traits(data).compute()
    result = result.sort_values('asset_path').asset_traits
    mask = result.notnull()
    result[mask] = result[mask] \
        .apply(lambda x: {k: sorted(v) for k, v in x.items()})
    result[result.isnull()] = 'null'
    result = result.tolist()
    expected = [
        dict(w=[0], x=[1, 2], y=[1, 2]),
        dict(w=[0], x=[1, 2], y=[1, 2]),
        dict(x=[1, 2], y=[1, 2], z=[1, 2]),
        dict(x=[1, 2], y=[1, 2], z=[1, 2]),
        'null',
    ]
    assert result == expected


def test_add_asset_id(db_cluster, specs):
    Spec001, Spec002, _ = specs
    data = [
        [
            Spec001,
            '/tmp/p-proj001_s-spec001_d-desc_v001/p-proj001_s-spec001_d-desc_v001_c0000-0000_f0001.png',  # noqa E501
            np.nan,
        ],
        [
            Spec001,
            '/tmp/p-proj001_s-spec001_d-desc_v001/p-proj001_s-spec001_d-desc_v001_c0000-0000_f0002.png',  # noqa E501
            np.nan,
        ],
        [
            Spec002,
            '/tmp/p-proj002_s-spec002_d-MASTER_v001/p-proj002_s-spec002_d-MASTER_v001_f0001.png',  # noqa E501
            'file_Error',
        ],
        [
            Spec002,
            '/tmp/p-proj002_s-spec002_d-desc_v001/p-proj002_s-spec002_d-desc_v001_f0002.png',
            np.nan,
        ],
        [
            np.nan,
            '/tmp/proj002/misc.txt',
            'file_Error',
        ],
    ]

    data = DataFrame(data)
    data.columns = ['specification_class', 'filepath', 'file_error']

    db_tools.add_asset_id(data)
    result = data['asset_id'].dropna().nunique()
    assert result == 2


def test_add_asset_name(db_cluster, specs):
    Spec001, Spec002, _ = specs
    data = [
        [
            Spec001,
            '/tmp/p-proj001_s-spec001_d-desc_v001/p-proj001_s-spec001_d-desc_v001_c0000-0000_f0001.png',  # noqa E501
            np.nan,
        ],
        [
            Spec001,
            '/tmp/p-proj001_s-spec001_d-desc_v001/p-proj001_s-spec001_d-desc_v001_c0000-0000_f0002.png',  # noqa E501
            np.nan,
        ],
        [
            Spec002,
            '/tmp/p-proj002_s-spec002_d-MASTER_v001/p-proj002_s-spec002_d-MASTER_v001_f0001.png',  # noqa E501
            'file_Error',
        ],
        [
            Spec002,
            '/tmp/p-proj002_s-spec002_d-desc_v001/p-proj002_s-spec002_d-desc_v001_f0002.png',
            np.nan,
        ],
        [
            np.nan,
            '/tmp/proj002/misc.txt',
            'file_Error',
        ],
    ]

    data = DataFrame(data)
    data.columns = ['specification_class', 'filepath', 'file_error']
    data = dd.from_pandas(data, npartitions=NUM_PARTITIONS)

    result = db_tools.add_asset_name(data).compute()
    result = result['asset_name'].dropna().nunique()
    assert result == 2


def test_add_asset_path(db_cluster, specs):
    Spec001, Spec002, _ = specs
    data = [
        [
            Spec001,
            '/tmp/p-proj001_s-spec001_d-desc_v001/p-proj001_s-spec001_d-desc_v001_c0000-0000_f0001.png',  # noqa E501
            np.nan,
        ],
        [
            Spec001,
            '/tmp/p-proj001_s-spec001_d-desc_v001/p-proj001_s-spec001_d-desc_v001_c0000-0000_f0002.png',  # noqa E501
            np.nan,
        ],
        [
            Spec002,
            '/tmp/p-proj002_s-spec002_d-MASTER_v001/p-proj002_s-spec002_d-MASTER_v001_f0001.png',  # noqa E501
            'file_Error',
        ],
        [
            Spec002,
            '/tmp/p-proj002_s-spec002_d-desc_v001/p-proj002_s-spec002_d-desc_v001_f0002.png',
            np.nan,
        ],
        [
            np.nan,
            '/tmp/proj002/misc.txt',
            'file_Error',
        ],
    ]

    data = DataFrame(data)
    data.columns = ['specification_class', 'filepath', 'file_error']
    expected = data.filepath\
        .apply(lambda x: Path(x).parent).apply(str).tolist()
    expected[-1] = 'nan'

    data = dd.from_pandas(data, npartitions=NUM_PARTITIONS)

    results = db_tools.add_asset_path(data).compute()
    result = results['asset_path'].apply(str).tolist()
    assert result == expected

    result = results['asset_path'].dropna().nunique()
    assert result == 3


def test_add_relative_path(db_cluster):
    data = DataFrame()
    data['foo'] = [
        '/foo/bar/taco.txt',
        '/foo/bar/kiwi.txt',
        '/tmp/pizza.txt',
    ]
    data = dd.from_pandas(data, npartitions=NUM_PARTITIONS)

    result = db_tools \
        .add_relative_path(data, 'foo', '/foo/bar') \
        .compute()['foo_relative'].tolist()
    expected = [
        'taco.txt',
        'kiwi.txt',
        '/tmp/pizza.txt',
    ]
    assert result == expected

    del data['foo_relative']
    result = db_tools \
        .add_relative_path(data, 'foo', '/foo/bar/') \
        .compute()['foo_relative'].tolist()
    expected = [
        'taco.txt',
        'kiwi.txt',
        '/tmp/pizza.txt',
    ]
    assert result == expected


def test_add_asset_type(db_cluster):
    data = DataFrame()
    data['specification_class'] = [
        Spec001,
        Spec002,
        Spec003,
        np.nan,
    ]
    data = dd.from_pandas(data, npartitions=NUM_PARTITIONS)

    result = db_tools.add_asset_type(data).compute()
    result = result['asset_type'].fillna('null').tolist()
    expected = ['file', 'sequence', 'complex', 'null']
    assert result == expected


def test_cleanup(db_cluster, db_columns):
    data = DataFrame()
    result = db_tools.cleanup(data).columns.tolist()
    assert result == db_columns

    data['filepath'] = [np.nan, Path('/foo/bar'), Path('/bar/foo')]
    expected = [np.nan, '/foo/bar', '/bar/foo']
    result = db_tools.cleanup(data).filepath.tolist()
    assert result == expected

    result = db_tools.cleanup(data).columns.tolist()
    assert result == db_columns


def test_validate_assets(db_cluster, db_data, make_files):
    data = db_data.head(1).copy()
    traits = dict(
        project=['proj001'],
        specification=['spec001'],
        descriptor=['desc'],
        version=[1],
        coordinate=[[0, 1]],
        frame=[5],
        extension=['png'],
        height=[5],
        width=[4],
        channels=[3],
    )
    data['asset_traits'] = [traits]

    # add bad asset
    bad = data.copy()
    bad_traits = deepcopy(traits)
    bad_traits['descriptor'] = ['kiwi']
    bad_traits['height'] = [99]
    bad['asset_traits'] = [bad_traits]
    bad['asset_id'] = 1
    cols = ['asset_name', 'asset_path', 'filename']
    bad[cols] = bad[cols].applymap(lambda x: re.sub('pizza', 'kiwi', x))
    data = pd.concat([data, bad], ignore_index=True)

    cols = [
        'asset_traits',
        'specification_class',
        'file_error',
        'specification',
    ]
    data = data[cols]
    data['file_error'] = np.nan

    data = dd.from_pandas(data, npartitions=NUM_PARTITIONS)

    result = db_tools.validate_assets(data).compute().reset_index(drop=True)

    # columns
    cols = ['asset_error', 'asset_valid']
    for expected in cols:
        assert expected in result.columns.tolist()

    # asset_valid
    assert bool(result.loc[0, 'asset_valid']) is True
    assert bool(result.loc[1, 'asset_valid']) is False

    # asset_error
    assert pd.isnull(result.loc[0, 'asset_error']) is True
    assert re.search('99 != 5', result.loc[1, 'asset_error']) is not None


def test_validate_assets_invalid_one_file(db_cluster, db_data, make_files):
    data = db_data.head(1).copy()
    traits = dict(
        project=['proj001'],
        specification=['spec001'],
        descriptor=['desc'],
        version=[1],
        coordinate=[[0, 1]],
        frame=[5],
        extension=['png'],
        height=[5],
        width=[40],
        channels=[3],
    )
    data['asset_traits'] = [traits]
    data = dd.from_pandas(data, npartitions=NUM_PARTITIONS)

    result = db_tools.validate_assets(data).compute().reset_index()
    for _, row in result.iterrows():
        assert re.search('40 != 4', row.asset_error) is not None
        assert row.asset_valid is False


def test_validate_assets_invalid_many_file(db_cluster, db_data, make_files):
    data = db_data.head(2).copy()
    traits = dict(
        project=['proj001', 'proj001'],
        specification=['spec001', 'spec001'],
        descriptor=['desc', 'desc'],
        version=[1, 1],
        coordinate=[[0, 1], [0, 1]],
        frame=[5, 5],
        extension=['png', 'png'],
        height=[5, 5],
        width=[4, 400],
        channels=[3, 3],
    )
    data['asset_traits'] = [traits, traits]
    data = dd.from_pandas(data, npartitions=NUM_PARTITIONS)

    result = db_tools.validate_assets(data).compute().reset_index()
    for _, row in result.iterrows():
        assert re.search('400 != 4', row.asset_error) is not None
        assert row.asset_valid is False


def test_get_data_for_write():
    data = lbt.relative_path(__file__, '../../../resources/fake_data.csv')
    data = pd.read_csv(data)

    file_data, asset_meta, file_meta, asset_chunk, file_chunk = db_tools \
        .get_data_for_write(data, '/tmp/projects', '/tmp/hidebound')

    data = data[data.asset_valid]

    expected = data.shape[0]
    assert file_data.shape[0] == expected
    assert file_meta.shape[0] == expected

    expected = data.asset_path.nunique()
    assert asset_meta.shape[0] == expected

    expected = set(data.filename.tolist())
    result = file_data.target.apply(lambda x: Path(x).name).tolist()
    result = set(result)
    assert result == expected

    file_meta.metadata.apply(json.dumps)
    asset_meta.metadata.apply(json.dumps)

    result = file_data.source\
        .apply(lambda x: '/tmp/projects' in x).unique().tolist()
    assert result == [True]

    for item in [file_data, file_meta, asset_meta]:
        result = item.target\
            .apply(lambda x: '/tmp/hidebound' in x).unique().tolist()
        assert result == [True]

    # ensure these columns do not have list values
    cols = ['asset_name', 'asset_path', 'asset_type', 'asset_traits']
    types = [str, str, str, dict]
    for type_, col in zip(types, cols):
        result = asset_meta['metadata']\
            .apply(lambda x: x[col])\
            .apply(lambda x: isinstance(x, list))\
            .tolist()
        for r in result:
            assert r is False

    # check asset_path root conversions
    temp = asset_meta['metadata'].apply(lambda x: x['asset_path']).tolist()
    for result in temp:
        assert result.startswith('/tmp/hidebound/content') is True

    # check filepath root conversions
    temp = file_meta['metadata'].apply(lambda x: x['filepath']).tolist()
    for result in temp:
        assert result.startswith('/tmp/hidebound/content') is True

    # asset chunk
    assert len(asset_chunk) == 1

    result = asset_chunk['target'].tolist()[0]
    assert 'hidebound-asset-chunk' in result

    expected = asset_meta.metadata.tolist()
    result = asset_chunk.metadata.tolist()[0]
    assert result == expected

    # file chunk
    assert len(file_chunk) == 1

    result = file_chunk['target'].tolist()[0]
    assert 'hidebound-file-chunk' in result

    expected = file_meta.metadata.tolist()
    result = file_chunk.metadata.tolist()[0]
    assert result == expected


def test_get_data_for_write_dirs():
    data = lbt.relative_path(__file__, '../../../resources/fake_data.csv')
    data = pd.read_csv(data)

    file_data, asset_meta, file_meta, asset_chunk, file_chunk = db_tools \
        .get_data_for_write(
            data,
            '/tmp/projects',
            '/tmp/hidebound'
        )

    result = file_data.target \
        .apply(lambda x: '/tmp/hidebound/content' in x).unique().tolist()
    assert result == [True]

    result = file_meta.target \
        .apply(lambda x: '/tmp/hidebound/metadata/file' in x) \
        .unique().tolist()
    assert result == [True]

    result = asset_meta.target \
        .apply(lambda x: '/tmp/hidebound/metadata/asset' in x) \
        .unique().tolist()
    assert result == [True]

    result = asset_chunk.target \
        .apply(lambda x: '/tmp/hidebound/metadata/asset-chunk' in x) \
        .unique().tolist()
    assert result == [True]

    result = file_chunk.target \
        .apply(lambda x: '/tmp/hidebound/metadata/file-chunk' in x) \
        .unique().tolist()
    assert result == [True]


def test_get_data_for_write_empty_dataframe():
    data = DataFrame()
    data['asset_valid'] = [False, False]

    result = db_tools.get_data_for_write(
        data, '/tmp/projects', '/tmp/hidebound'
    )
    assert result is None


def test_get_data_for_write_asset_id_file_ids_pair():
    data = lbt.relative_path(__file__, '../../../resources/fake_data.csv')
    data = pd.read_csv(data, index_col=0)

    _, a, b, _, _ = db_tools \
        .get_data_for_write(
            data,
            '/tmp/projects',
            '/tmp/hidebound'
        )

    a['asset_id'] = a.metadata.apply(lambda x: x['asset_id'])
    a['file_ids'] = a.metadata.apply(lambda x: x['file_ids'])
    keys = sorted(a.asset_id.tolist())
    vals = sorted(a.file_ids.tolist())
    a = dict(zip(keys, vals))

    b['asset_id'] = b.metadata.apply(lambda x: x['asset_id'])
    b['file_ids'] = b.metadata.apply(lambda x: x['file_id'])
    b = b.groupby('asset_id', as_index=False).agg(lambda x: x.tolist())
    keys = sorted(b.asset_id.tolist())
    vals = sorted(b.file_ids.tolist())
    b = dict(zip(keys, vals))

    assert a == b
