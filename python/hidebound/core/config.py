from typing import Union  # noqa F401

from copy import copy
from importlib import import_module
import inspect
import os
from pathlib import Path
import sys

from schematics.exceptions import ValidationError
from schematics.types import (
    BaseType, BooleanType, DictType, IntType, ListType, ModelType, StringType,
    URLType
)
from schematics import Model

from hidebound.core.connection import DaskConnectionConfig
from hidebound.core.specification_base import SpecificationBase
from hidebound.exporters.disk_exporter import DiskConfig
from hidebound.exporters.girder_exporter import GirderConfig
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
    if not isinstance(mod.SPECIFICATIONS, list):
        sys.path = temp
        msg = f'{filepath.as_posix()} SPECIFICATIONS attribute is not a list.'
        raise ValidationError(msg)

    # ensure all SPECIFICATIONS are subclasses of SpecificationBase
    errors = list(filter(
        lambda x: not inspect.isclass(x) or not issubclass(x, SpecificationBase),
        mod.SPECIFICATIONS
    ))
    if len(errors) > 0:
        sys.path = temp
        msg = f'{errors} are not subclasses of SpecificationBase.'
        raise ValidationError(msg)

    sys.path = temp
# ------------------------------------------------------------------------------


class Config(Model):
    r'''
    A class for validating configurations supplied to Database.

    Attributes:
        ingress_directory (str or Path): Root directory to recurse.
        staging_directory (str or Path): Directory where hidebound data will be
            staged.
        include_regex (str, optional): Include filenames that match this regex.
            Default: ''.
        exclude_regex (str, optional): Exclude filenames that match this regex.
            Default: '\.DS_Store'.
        write_mode (str, optional): How assets will be extracted to
            hidebound/content directory. Default: copy.
        workflow (list[str], optional): Ordered steps of workflow.  Default:
            ['delete', 'update', 'create', 'export'].
        redact_regex (str, optional): Regex pattern matched to config keys.
            Values of matching keys will be redacted.
            Default: "(_key|_id|_token|url)$".
        redact_hash (bool, optional): Whether to replace redacted values with
            "REDACTED" or a hash of the value. Default: True.
        specification_files (list[str], optional): List of asset specification
            files. Default: [].
        exporters (dict, optional): Dictionary of exporter configs, where the
            key is the exporter name and the value is its config. Default: {}.
        webhooks (list[dict], optional): List of webhooks to be called after
            export. Default: [].
        dask (dict, optional). Dask configuration. Default: {}.
    '''
    ingress_directory = StringType(
        required=True, validators=[vd.is_directory]
    )  # type: StringType
    staging_directory = StringType(
        required=True, validators=[vd.is_directory, vd.is_hidebound_directory]
    )  # type: StringType
    include_regex = StringType(default='', required=True)  # type: StringType
    exclude_regex = StringType(default=r'\.DS_Store', required=True)  # type: StringType
    write_mode = StringType(
        required=True,
        validators=[lambda x: vd.is_in(x, ['copy', 'move'])],
        default="copy",
    )  # type: StringType
    dask = ModelType(
        DaskConnectionConfig, default={}, required=True
    )  # type: ModelType
    workflow = ListType(
        StringType(),
        required=True,
        validators=[vd.is_workflow],
        default=['delete', 'update', 'create', 'export']
    )  # type: ListType
    redact_regex = StringType(required=True, default='(_key|_id|_token|url)$')  # type: StringType
    redact_hash = BooleanType(required=True, default=True)  # type: BooleanType
    specification_files = ListType(
        StringType(validators=[is_specification_file, vd.is_file]),
        default=[],
        required=True
    )  # type: ListType
    exporters = ListType(
        BaseType(
            validators=[lambda x: vd.is_one_of(
                x, [DiskConfig, S3Config, GirderConfig]
            )]
        ),
        required=False,
        default=[],
    )  # type: ListType

    class WebhookConfig(Model):
        url = URLType(required=True, fqdn=False)  # type: URLType
        method = StringType(required=True, validators=[vd.is_http_method])  # type: StringType
        headers = DictType(StringType, required=False)  # type: DictType
        data = DictType(BaseType, required=False, serialize_when_none=False)  # type: DictType
        json = DictType(BaseType, required=False, serialize_when_none=False)  # type: DictType
        params = DictType(BaseType, required=False, serialize_when_none=False)  # type: DictType
        timeout = IntType(required=False, serialize_when_none=False)  # type: IntType
    webhooks = ListType(ModelType(WebhookConfig), required=False, default=[])  # type: ListType
