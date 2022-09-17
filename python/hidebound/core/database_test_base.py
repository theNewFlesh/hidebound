from typing import Any, List, Tuple, Union

from pathlib import Path
import os
import re
import unittest

from pandas import DataFrame
from schematics.types import ListType, IntType, StringType
import dask.dataframe as dd
import dask.distributed as ddist
import numpy as np
import pytest
import skimage.io

from hidebound.core.specification_base import SpecificationBase
import hidebound.core.traits as tr
import hidebound.core.validators as vd
# ------------------------------------------------------------------------------


# FIXTURES----------------------------------------------------------------------
@pytest.fixture(scope='module')
def db_client():
    cluster = ddist.LocalCluster(
        n_workers=1,
        threads_per_worker=2,
        dashboard_address='0.0.0.0:8087',
    )
    client = ddist.Client(cluster)
    yield client, cluster

    client.shutdown()


@pytest.fixture()
def db_columns():
    return _db_columns()


def _db_columns():
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
    return _db_data(temp_dir)


def _db_data(temp_dir):
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
    return _make_files(db_data)


def _make_files(db_data):
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
    return _dir_data(db_data)


def _dir_data(db_data):
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
    return _specs()


def _specs():
    # type: () -> Tuple[Any, Any, Any]
    '''
    Returns:
        tuple: Spec001, Spec002, BadSpec
    '''
    return Spec001, Spec002, BadSpec


@pytest.fixture()
def spec_file(temp_dir):
    return _spec_file(temp_dir)


def _spec_file(temp_dir):
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


# TEST-BASE---------------------------------------------------------------------
class DatabaseTestBase(unittest.TestCase):
    @property
    def columns(self):
        # type: () -> List[str]
        return _db_columns()

    def get_data(self, root, nans=False):
        # type: (str, bool) -> DataFrame
        data = _db_data(root)
        if nans:
            data = data.applymap(lambda x: np.nan if x is None else x)
        return data

    def create_files(self, root):
        # type: (Union[str, Path]) -> "DataFrame"
        root = Path(root).as_posix()
        data = self.get_data(root)
        _make_files(data)
        return data

    def get_directory_to_dataframe_data(self, root):
        # type: (str) -> "dd.DataFrame"
        data = self.get_data(root)
        return _dir_data(data)

    def get_specifications(self):
        # type: () -> Tuple[Any, Any, Any]
        return _specs()
