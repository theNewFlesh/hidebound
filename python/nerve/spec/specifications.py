#! /usr/bin/env python
import re
from nerve.spec.traits import *
from nerve.spec.validators import *
from schematics.models import Model, BaseType
from schematics.types import StringType, IntType, BooleanType
from schematics.types.compound import ListType, DictType
from schematics.exceptions import ValidationError
# ------------------------------------------------------------------------------

class MetaName(Model):
    project_name  = StringType(required=True, validators=[is_project_name])
    specification = StringType(required=True, validators=[is_specification])
    descriptor    = StringType(required=True, validators=[])
    version       = IntType(required=True, validators=[is_version])
    render_pass   = StringType(validators=[is_render_pass])
    frames        = ListType(BaseType, validators=[is_frame])
    coordinates   = DictType(BaseType, validators=[is_coordinate])
    meta          = StringType(required=True, validators=[is_meta])
# ------------------------------------------------------------------------------

class Specification(Model):
    def __init__(self, arg):
        arg['specification'] = self.__class__.__name__.lower()
        # needed because python doesn't support hyphenated attributes
        arg = {re.sub('-', '_', k): v for k,v in arg.items()}
        super().__init__(arg)

    specification = StringType(required=True)

class Config(Specification):
    username                 = StringType(required=True, validators=[is_username])
    user_branch              = StringType(required=True, validators=[is_user_branch])
    organization             = StringType(required=True, validators=[is_organization])
    project_root             = StringType(required=True, validators=[is_project_root])
    token                    = StringType(required=True, validators=[is_token])
    url_type                 = StringType(required=True, validators=[is_url_type])
    private                  = BooleanType(required=True, validators=[is_private])
    specification            = StringType(required=True, validators=[is_specification])
    request_include_patterns = ListType(StringType, default=[], validators=[is_request_include_patterns])
    request_exclude_patterns = ListType(StringType, default=[], validators=[is_request_exclude_patterns])
    publish_include_patterns = ListType(StringType, default=[], validators=[is_publish_include_patterns])
    publish_exclude_patterns = ListType(StringType, default=[], validators=[is_publish_exclude_patterns])
    extensions               = ListType(StringType, required=True, validators=[is_extension])
    assets                   = ListType(StringType, default=[], validators=[])
    deliverables             = ListType(StringType, required=True, validators=[is_specification])
    teams                    = DictType(StringType, required=True, validators=[is_teams])
    gitignore                = ListType(StringType, required=True, validators=[])

class Project(Specification):
    project_name = StringType(required=True, validators=[is_project_name])
    project_id   = StringType(required=True, validators=[is_project_id])
    url          = StringType(required=True, validators=[is_url])
    notes        = StringType(default='')

    version      = IntType(required=True, validators=[is_version])

class Asset(Specification):
    project_name = StringType(required=True, validators=[is_project_name])
    project_id   = StringType(required=True, validators=[is_project_id])
    url          = StringType(required=True, validators=[is_url])
    notes        = StringType(default='')
    deliverable  = BooleanType(default=False)

class Deliverable(Specification):
    project_name = StringType(required=True, validators=[is_project_name])
    project_id   = StringType(required=True, validators=[is_project_id])
    url          = StringType(required=True, validators=[is_url])
    notes        = StringType(default='')

    version      = IntType(required=True, validators=[is_version])
    asset_name   = StringType(required=True, validators=[])
    asset_id     = StringType(required=True, validators=[is_asset_id])
    data         = ListType(StringType, validators=[is_file, is_path, is_exists])
    descriptor   = StringType(required=True, validators=[is_descriptor])
    dependencies = ListType(StringType, default=[])
    deliverable  = BooleanType(default=True)
# ------------------------------------------------------------------------------

class Config001(Config):
    pass

class Proj001(Project):
    pass

class Vol001(Deliverable):
    pass

class Geo001(Deliverable):
    pass
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

__all__ = [
    'Config001',
    'Proj001',
    'Vol001'
]

if __name__ == '__main__':
    main()
