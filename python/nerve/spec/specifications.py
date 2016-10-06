#! /usr/bin/env python
from nerve.spec.traits import *
from nerve.spec.validators import *
from schematics.models import Model, BaseType
from schematics.types import StringType, IntType
from schematics.types.compound import ListType, DictType
from schematics.exceptions import ValidationError
# ------------------------------------------------------------------------------

class BaseModel(Model):
    def __init__(self, *args, **kwargs):
        self.specification = self.__class__.__name__.lower()
        super().__init__(*args, **kwargs)

    project_name = StringType(required=True, validators=[is_project_name])
    project_id = StringType(required=True, validators=[is_project_id])
    url = StringType(required=True, validators=[is_url])
    notes = StringType(default='')

class Project(BaseModel):
  version = IntType(required=True, validators=[is_version])

class Asset(BaseModel):
    pass

class Deliverable(BaseModel):
    version = IntType(required=True, validators=[is_version])
    asset_name = StringType(required=True, validators=[is_asset_name])
    asset_id = StringType(required=True, validators=[is_asset_id])
    data = ListType(BaseType, validators=[is_data])
    descriptor = StringType(default='')
    dependencies = ListType(BaseType, default=[])
    version = IntType(required=True, validators=[is_version])

class Proj001(Project):
    pass

class Vol001(Deliverable):
    pass
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

# __all__ = []

if __name__ == '__main__':
    main()
