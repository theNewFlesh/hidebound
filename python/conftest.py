from typing import Any, List, Tuple, Union

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import re

from pandas import DataFrame
from schematics.types import ListType, IntType, StringType
import dask.dataframe as dd
import dask.distributed as ddist
import flask
import lunchbox.tools as lbt
import numpy as np
import pytest
import skimage.io
import yaml

from hidebound.core.specification_base import SpecificationBase
import hidebound.core.traits as tr
import hidebound.core.validators as vd
import hidebound.server.extensions as ext
# ------------------------------------------------------------------------------


# APP---------------------------------------------------------------------------
@pytest.fixture()
def env(config):
    yaml_keys = [
        'specification_files',
        'exporters',
        'webhooks',
    ]
    for key, val in config.items():
        if key in yaml_keys:
            os.environ[f'HIDEBOUND_{key.upper()}'] = yaml.safe_dump(val)
        else:
            os.environ[f'HIDEBOUND_{key.upper()}'] = str(val)

    keys = filter(lambda x: x.startswith('HIDEBOUND_'), os.environ.keys())
    env = {k: os.environ[k] for k in keys}
    yield env

    keys = filter(lambda x: x.startswith('HIDEBOUND_'), os.environ.keys())
    for key in keys:
        os.environ.pop(key)


@pytest.fixture()
def app():
    context = flask.Flask(__name__).app_context()
    context.push()
    app = context.app
    app.config['TESTING'] = True

    yield app

    context.pop()


@pytest.fixture()
def client(app):
    # set instance members
    client = app.test_client()
    yield client


@pytest.fixture()
def extension(app, make_dirs):
    app.config['TESTING'] = False
    ext.swagger.init_app(app)
    ext.hidebound.init_app(app)
    yield ext.hidebound


@pytest.fixture()
def temp_dir():
    temp = TemporaryDirectory()
    yield temp.name
    temp.cleanup()


@pytest.fixture()
def make_dirs(temp_dir):
    ingress = Path(temp_dir, 'ingress').as_posix()
    staging = Path(temp_dir, 'hidebound').as_posix()
    archive = Path(temp_dir, 'archive').as_posix()

    # creates dirs
    os.makedirs(ingress)
    os.makedirs(staging)
    os.makedirs(archive)

    yield ingress, staging, archive


@pytest.fixture()
def config(temp_dir):
    spec = '../hidebound/hidebound/core/test_specifications.py'
    if 'REPO_ENV' in os.environ:
        spec = '../python/hidebound/core/test_specifications.py'
    spec = lbt.relative_path(__file__, spec).absolute().as_posix()

    config = dict(
        ingress_directory=Path(temp_dir, 'ingress').as_posix(),
        staging_directory=Path(temp_dir, 'hidebound').as_posix(),
        include_regex='',
        exclude_regex=r'\.DS_Store',
        write_mode='copy',
        dask_enabled=False,
        dask_workers=3,
        redact_regex='(_key|_id|url)$',
        redact_hash=True,
        workflow=['update', 'create', 'export', 'delete'],
        specification_files=[spec],
        exporters=[
            dict(
                name='disk',
                target_directory=Path(temp_dir, 'archive').as_posix(),
                metadata_types=['asset', 'file', 'asset-chunk', 'file-chunk']
            )
        ],
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
    return config


@pytest.fixture()
def config_yaml_file(temp_dir, config):
    filepath = Path(temp_dir, 'hidebound_config.yaml').as_posix()
    with open(filepath, 'w') as f:
        yaml.safe_dump(config, f)

    os.environ['HIDEBOUND_CONFIG_FILEPATH'] = filepath
    return filepath


@pytest.fixture()
def config_json_file(temp_dir, config):
    filepath = Path(temp_dir, 'hidebound_config.json').as_posix()
    with open(filepath, 'w') as f:
        json.dump(config, f)

    os.environ['HIDEBOUND_CONFIG_FILEPATH'] = filepath
    return filepath


# DATABASE----------------------------------------------------------------------
@pytest.fixture(scope='module')
def dask_client():
    cluster = ddist.LocalCluster(n_workers=2, threads_per_worker=1)
    client = ddist.Client(cluster)
    yield client

    client.close()
    cluster.close()


@pytest.fixture()
def db_columns():
    # type: () -> List[str]
    '''
    Returns:
        List[str]: List of DB columns.
    '''
    return [
        'specification',
        'extension',
        'filename',
        'filepath',
        'file_error',
        'file_traits',
        'asset_name',
        'asset_path',
        'asset_type',
        'asset_traits',
        'asset_error',
        'asset_valid',
    ]


@pytest.fixture()
def db_data(temp_dir):
    # type: (str) -> DataFrame
    '''
    Creates a fake database DataFrame.

    Args:
        temp_dir (str): Ingress directory.

    Returns:
        DataFrame: DB data.
    '''
    data = [
        [0, True,  'sequence', 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v001', 'p-proj001_s-spec001_d-pizza_v001_c0000-0001_f0001.png',  None                                ],  # noqa E501 E241
        [0, True,  'sequence', 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v001', 'p-proj001_s-spec001_d-pizza_v001_c0000-0001_f0002.png',  None                                ],  # noqa E501 E241
        [0, True,  'sequence', 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v001', 'p-proj001_s-spec001_d-pizza_v001_c0000-0001_f0003.png',  None                                ],  # noqa E501 E241
        [1, True,  'sequence', 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c0000-0000_f0001.png',  None                                ],  # noqa E501 E241
        [1, True,  'sequence', 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c0000-0000_f0002.png',  None                                ],  # noqa E501 E241
        [1, True,  'sequence', 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c0000-0000_f0003.png',  None                                ],  # noqa E501 E241
        [1, True,  'sequence', 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c0000-0000_f0004.png',  None                                ],  # noqa E501 E241
        [2, True,  'sequence', 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c0000-0001_f0001.png',  None                                ],  # noqa E501 E241
        [2, True,  'sequence', 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c0000-0001_f0002.png',  None                                ],  # noqa E501 E241
        [2, True,  'sequence', 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c0000-0001_f0003.png',  None                                ],  # noqa E501 E241
        [2, True,  'sequence', 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v002', 'p-proj001_s-spec001_d-pizza_v002_c0000-0001_f0004.png',  None                                ],  # noqa E501 E241
        [3, False, 'sequence', 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-kiwi_v003_c0000-0001_f0001.png', ' Inconsistent descriptor field token'],  # noqa E501 E241
        [3, False, 'sequence', 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-pizza_v003_c0000-0001_f0002.png',  None                                ],  # noqa E501 E241
        [3, False, 'sequence', 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-PIZZA_v003_c0000-0001_f0003.png',  'Illegal descriptor field token'    ],  # noqa E501 E241
        [3, False, 'sequence', 'spec001', 'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec001_d-pizza_v003_c0000-0001_f0004.png',  None                                ],  # noqa E501 E241
        [3, False, np.nan,     None,      'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'p-proj001_s-spec0001_d-pizza_v003_c0000-0001_f0005.png', 'Illegal specification field token' ],  # noqa E501 E241
        [3, False, np.nan,     None,      'proj001/spec001/pizza/p-proj001_s-spec001_d-pizza_v003', 'misc.txt',                                               'SpecificationBase not found'       ],  # noqa E501 E241
        [4, True,  'sequence', 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v001',   'p-proj001_s-spec002_d-taco_v001_f0000.jpg',              None                                ],  # noqa E501 E241
        [4, True,  'sequence', 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v001',   'p-proj001_s-spec002_d-taco_v001_f0001.jpg',              None                                ],  # noqa E501 E241
        [4, True,  'sequence', 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v001',   'p-proj001_s-spec002_d-taco_v001_f0002.jpg',              None                                ],  # noqa E501 E241
        [5, False, 'sequence', 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v001_f0000.jpg',              'Invalid asset directory name'      ],  # noqa E501 E241
        [5, False, 'sequence', 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v002_f0001.jpg',              None                                ],  # noqa E501 E241
        [5, False, 'sequence', 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v002',                        'Expected "_"'                      ],  # noqa E501 E241
        [5, False, 'sequence', 'spec002', 'proj001/spec002/taco/p-proj001_s-spec002_d-taco_v002',   'p-proj001_s-spec002_d-taco_v02_f0003.jpg',               'Illegal version field token'       ],  # noqa E501 E241
        [6, False, 'sequence', 'vdb001',  'proj002/vdb001',                                         'p-proj002_s-vdb001_d-bagel_v001.vdb',                    'Specification not found'           ],  # noqa E501 E241
        [6, False, 'sequence', 'vdb001',  'proj002/vdb001',                                         'p-proj002_s-vdb001_d-bagel_v002.vdb',                    'Specification not found'           ],  # noqa E501 E241
        [6, False, 'sequence', 'vdb001',  'proj002/vdb001',                                         'p-proj002_s-vdb001_d-bagel_v003.vdb',                    'Specification not found'           ],  # noqa E501 E241
    ]  # type: Any
    ingress = Path(temp_dir, 'ingress').as_posix()

    data = DataFrame(data)
    data.columns = [
        'asset_id', 'asset_valid', 'asset_type', 'specification',
        'asset_path', 'filename', 'file_error'
    ]

    data.asset_path = data.asset_path.apply(lambda x: ingress + '/' + x)
    data['asset_name'] = data.asset_path.apply(lambda x: x.split('/')[-1])

    data['filepath'] = data\
        .apply(lambda x: Path(ingress, x.asset_path, x.filename), axis=1)

    specs = {
        Spec001.name: Spec001,
        Spec002.name: Spec002,
        None: np.nan,
        'vdb001': np.nan,
    }
    data['specification_class'] = data.specification\
        .apply(lambda x: specs[x])
    return data


@pytest.fixture()
def make_files(db_data):
    # type: (DataFrame) -> List[str]
    '''
    Creates files in given DataFrame.

    Args:
        db_data (DataFrame): DataFrame with files.

    Returns:
        list[str]: List of filepaths.
    '''
    data = db_data
    for filepath in data.filepath.tolist():
        os.makedirs(filepath.parent, exist_ok=True)

        ext = Path(filepath).suffix.lstrip('.')
        if ext in ['png', 'jpg']:
            img = np.zeros((5, 4, 3), dtype=np.uint8)
            img[:, :, 2] = 128
            skimage.io.imsave(filepath.as_posix(), img)
        else:
            with open(filepath, 'w') as f:
                f.write('')

    return sorted(data.filepath.apply(lambda x: x.as_posix()).tolist())


@pytest.fixture()
def dir_data(db_data):
    # type: (DataFrame) -> "dd.DataFrame"
    '''
    Creates db_tools.dataframe_from_directory data given db_data.

    Args:
        db_data (DataFrame): DB data.

    Returns:
        DataFrame: directory_to_dataframe data.
    '''
    files = db_data
    data = DataFrame()
    data['filename'] = files.filename
    data['filepath'] = files.asset_path
    data.filepath = data\
        .apply(lambda x: Path(x.filepath, x.filename), axis=1)
    data['extension'] = files\
        .filename.apply(lambda x: Path(x).suffix.lstrip('.'))
    data = dd.from_pandas(data, chunksize=100)
    return data


@pytest.fixture()
def specs():
    # type: () -> Tuple[Any, Any, Any]
    '''
    Returns:
        tuple: Spec001, Spec002, BadSpec
    '''
    return Spec001, Spec002, BadSpec


@pytest.fixture()
def spec_file(temp_dir):
    os.makedirs(Path(temp_dir, 'specs'))
    spec_file = Path(temp_dir, 'specs', 'specs.py').as_posix()

    text = '''
        from schematics.types import IntType, ListType, StringType
        from hidebound.core.specification_base import SpecificationBase

        class Spec001(SpecificationBase):
            foo = ListType(IntType(), required=True)
            bar = ListType(StringType(), required=True)

        class Spec002(SpecificationBase):
            boo = ListType(IntType(), required=True)
            far = ListType(StringType(), required=True)

        SPECIFICATIONS = [Spec001, Spec002]'''
    text = re.sub('        ', '', text)
    with open(spec_file, 'w') as f:
        f.write(text)
    return spec_file


# SPECS-------------------------------------------------------------------------
class Spec001(SpecificationBase):
    name = 'spec001'
    filename_fields = [
        'project',
        'specification',
        'descriptor',
        'version',
        'coordinate',
        'frame',
        'extension',
    ]
    coordinate = ListType(ListType(IntType()), required=True)
    frame = ListType(IntType(), required=True)
    extension = ListType(
        StringType(),
        required=True,
        validators=[lambda x: vd.is_eq(x, 'png')]
    )

    height = ListType(
        IntType(),
        required=True, validators=[lambda x: vd.is_eq(x, 5)]
    )
    width = ListType(
        IntType(),
        required=True, validators=[lambda x: vd.is_eq(x, 4)]
    )
    channels = ListType(
        IntType(),
        required=True, validators=[lambda x: vd.is_eq(x, 3)]
    )

    file_traits = dict(
        width=tr.get_image_width,
        height=tr.get_image_height,
        channels=tr.get_num_image_channels,
    )

    def get_asset_path(self, filepath):
        return Path(filepath).parents[0]


class Spec002(SpecificationBase):
    name = 'spec002'
    filename_fields = [
        'project',
        'specification',
        'descriptor',
        'version',
        'frame',
        'extension',
    ]

    frame = ListType(IntType(), required=True)
    extension = ListType(
        StringType(),
        required=True,
        validators=[lambda x: vd.is_eq(x, 'jpg')]
    )

    height = ListType(
        IntType(),
        required=True, validators=[lambda x: vd.is_eq(x, 5)]
    )
    width = ListType(
        IntType(),
        required=True, validators=[lambda x: vd.is_eq(x, 4)]
    )
    channels = ListType(
        IntType(),
        required=True, validators=[lambda x: vd.is_eq(x, 3)]
    )

    file_traits = dict(
        width=tr.get_image_width,
        height=tr.get_image_height,
        channels=tr.get_num_image_channels,
    )

    def get_asset_path(self, filepath):
        return Path(filepath).parents[0]


class BadSpec:
    pass
