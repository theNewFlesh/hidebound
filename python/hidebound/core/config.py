from typing import Union  # noqa F401

from copy import copy
from importlib import import_module
import inspect
import os
from pathlib import Path
import sys

from schematics.exceptions import ValidationError
from schematics.types import (
    BaseType, DictType, ListType, ModelType, StringType, URLType
)
from schematics import Model

from hidebound.core.specification_base import SpecificationBase
from hidebound.exporters.girder_exporter import GirderConfig
from hidebound.exporters.local_disk_exporter import LocalDiskConfig
from hidebound.exporters.s3_exporter import S3Config
import hidebound.core.validators as vd
# ------------------------------------------------------------------------------


# must be in here to avoid circular import
def is_specification_file(filepath):
    # type: (Union[str, Path]) -> None
    '''
    Validator for specification files given to Database.

    Args:
        filepath (str or Path): Filepath of python specification file.

    Raises:
        ValidationError: If module could not be imported.
        ValidationError: If module has no SPECIFICATIONS attribute.
        ValidationError: If module SPECIFICATIONS attribute is not a list.
        ValidationError: If modules classes in SPECIFICATIONS attribute are not
            subclasses of SpecificationBase.
        ValidationError: If keys in SPECIFICATIONS attribute are not lowercase
            versions of class names.
    '''
    # get module name
    filepath = Path(filepath)
    filename = filepath.name
    filename, _ = os.path.splitext(filename)

    # append module parent to sys.path
    parent = filepath.parent.as_posix()
    temp = copy(sys.path)
    sys.path.append(parent)

    # import module
    mod = None
    try:
        mod = import_module(filename, filepath)  # type: ignore
    except Exception:
        sys.path = temp
        msg = f'{filepath.as_posix()} could not be imported.'
        raise ValidationError(msg)

    # get SPECIFICATIONS
    if not hasattr(mod, 'SPECIFICATIONS'):
        sys.path = temp
        msg = f'{filepath.as_posix()} has no SPECIFICATIONS attribute.'
        raise ValidationError(msg)

    # ensure SPECIFICATIONS is a list
    if not isinstance(mod.SPECIFICATIONS, list):  # type: ignore
        sys.path = temp
        msg = f'{filepath.as_posix()} SPECIFICATIONS attribute is not a list.'
        raise ValidationError(msg)

    # ensure all SPECIFICATIONS are subclasses of SpecificationBase
    errors = list(filter(
        lambda x: not inspect.isclass(x) or not issubclass(x, SpecificationBase),
        mod.SPECIFICATIONS   # type: ignore
    ))
    if len(errors) > 0:
        sys.path = temp
        msg = f'{errors} are not subclasses of SpecificationBase.'
        raise ValidationError(msg)

    sys.path = temp


def is_hidebound_directory(directory):
    # type: (Union[str, Path]) -> None
    '''
    Ensures directory name is "hidebound".

    Args:
        directory (str or Path): Hidebound directory.

    Raises:
        ValidationError: If directory is not named "hidebound".
    '''
    if Path(directory).name != 'hidebound':
        msg = f'{directory} directory is not named hidebound.'
        raise ValidationError(msg)


def is_http_method(method):
    # type: (str) -> None
    '''
    Ensures given method is a legal HTTP method.
    Legal methods include:

        * get
        * put
        * post
        * delete
        * patch

    Args:
        method (str): HTTP method.

    Raises:
        ValidationError: If method is not a legal HTTP method.
    '''
    methods = ['get', 'put', 'post', 'delete', 'patch']
    if method not in methods:
        msg = f'{method} is not a legal HTTP method. Legal methods: {methods}.'
        raise ValidationError(msg)
# ------------------------------------------------------------------------------


class Config(Model):
    r'''
    A class for validating configurations supplied to Database.

    Attributes:
        root_directory (str or Path): Root directory to recurse.
        hidebound_directory (str or Path): Directory where hidebound data will
            be saved.
        specification_files (list[str], optional): List of asset specification
            files. Default: [].
        include_regex (str, optional): Include filenames that match this regex.
            Default: ''.
        exclude_regex (str, optional): Exclude filenames that match this regex.
            Default: '\.DS_Store'.
        write_mode (str, optional): How assets will be extracted to
            hidebound/content directory. Default: copy.
        exporters (dict, optional): Dictionary of exporter configs, where the
            key is the exporter name and the value is its config. Default: {}.
    '''
    root_directory = StringType(
        required=True, validators=[vd.is_directory]
    )  # type: StringType
    hidebound_directory = StringType(
        required=True, validators=[vd.is_directory, is_hidebound_directory]
    )  # type: StringType
    specification_files = ListType(
        StringType(validators=[is_specification_file, vd.is_file]),
        default=[],
        required=True
    )  # type: ListType
    include_regex = StringType(default='', required=True)  # type: StringType
    exclude_regex = StringType(default=r'\.DS_Store', required=True)  # type: StringType
    write_mode = StringType(
        required=True,
        validators=[lambda x: vd.is_in(x, ['copy', 'move'])],
        default="copy",
    )  # type: StringType

    class ExportersConfig(Model):
        girder = ModelType(
            GirderConfig, required=False, serialize_when_none=False
        )  # type: ModelType
        s3 = ModelType(
            S3Config, required=False, serialize_when_none=False
        )  # type: ModelType
        local_disk = ModelType(
            LocalDiskConfig, required=False, serialize_when_none=False
        )  # type: ModelType
    exporters = ModelType(ExportersConfig, required=False, default={})  # type: ModelType

    class WebhookConfig(Model):
        url = URLType(required=True)  # type: URLType
        method = StringType(required=True, validators=[is_http_method])  # type: StringType
        headers = DictType(StringType, required=False)  # type: DictType
        data = DictType(BaseType, required=False, serialize_when_none=False)  # type: DictType
        json = DictType(BaseType, required=False, serialize_when_none=False)  # type: DictType
        params = DictType(BaseType, required=False, serialize_when_none=False)  # type: DictType
    webhooks = ListType(ModelType(WebhookConfig), required=False, default=[])  # type: ListType
