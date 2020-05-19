from copy import copy
from importlib import import_module
import inspect
import os
from pathlib import Path
import sys

from schematics.exceptions import ValidationError
from schematics.types import ListType, StringType
from schematics import Model

from hidebound.core.specification_base import SpecificationBase
import hidebound.core.validators as vd
# ------------------------------------------------------------------------------


# must be in here to avoid circular import
def is_specification_file(filepath):
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
        mod = import_module(filename, filepath)
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
        lambda x: not inspect.isclass(x) or not issubclass(x, SpecificationBase), mod.SPECIFICATIONS
    ))
    if len(errors) > 0:
        sys.path = temp
        msg = f'{errors} are not subclasses of SpecificationBase.'
        raise ValidationError(msg)

    sys.path = temp


def is_hidebound_directory(directory):
    '''
    Ensures directory name is "hidebound".

    Args:
        directory (str or Path): Hidebound directory.

    Raises:
        ValidationError: If directory is not named "hidebound".
    '''
    if Path(directory).name != 'hidebound':
        msg = f'{directory} directory is not named hidebound.core.'
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
            hidebound/data directory. Default: copy.
    '''
    root_directory = StringType(required=True, validators=[vd.is_directory])
    hidebound_directory = StringType(
        required=True, validators=[vd.is_directory, is_hidebound_directory]
    )
    specification_files = ListType(
        StringType(validators=[is_specification_file, vd.is_file]),
        default=[],
        required=True
    )
    include_regex = StringType(default='', required=True)
    exclude_regex = StringType(default=r'\.DS_Store', required=True)
    write_mode = StringType(
        required=True,
        validators=[lambda x: vd.is_in(x, ['copy', 'move'])],
        default="copy",
    )
