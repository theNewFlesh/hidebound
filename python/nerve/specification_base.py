#! /usr/bin/env python
'''
The base module houses all the base specifications for nerve entities

Those entities include: configs, projects, deliverables and deliverables.

All specifications used in production should be subclassed from the
aforementioned classes.  All class attributes must have a "get_[attribute]"
function in the traits module and should have one or more validators related t
the value of that trait (especially if required).
'''
# ------------------------------------------------------------------------------

import re
# import nerve
# from nerve.utils import conform_keys
from nerve.validators import *
from schematics.models import Model, BaseType
from schematics.types import StringType, IntType, BooleanType, URLType
from schematics.types.compound import ListType, DictType, ModelType
from schematics.exceptions import ValidationError
# ------------------------------------------------------------------------------

class Specification(Model):
    '''
        Base class from which all nerve specifications are subclassed.
    '''
    specification = StringType(required=True, validators=[is_specification])

    def __init__(self, data):
        '''
        Creates a Specification instance.

        Attributes:
            name (str): Same as class name.

        Args:
            data (dict): Dictionary of specification values.

        Returns:
            name
        '''
        if 'name' not in data.keys():
            data['name'] = self.__class__.__name__.lower()
        super().__init__(raw_data=data)


# class MetaName(Specification):
#     '''
#     Used for validating a metadata file's name

#     A convenience class used by is_metapath in the validators module
#     '''
#     project_name  = StringType(required=True, validators=[is_project_name])
#     specification = StringType(required=True, validators=[is_specification])
#     descriptor    = StringType(required=True, validators=[])
#     version       = IntType(required=True, validators=[is_version])
#     render_pass   = StringType(validators=[is_render_pass])
#     coordinate    = DictType(BaseType, validators=[is_coordinate])
#     frame         = ListType(BaseType, validators=[is_frame])
#     meta          = BooleanType(required=True, validators=[is_meta])
#     extension     = StringType(required=True, default='yml', validators=[is_metadata_extension])
# # ------------------------------------------------------------------------------

# class ProjectTemplate(Specification):
#     '''
#     Project templates are used as overidable defaults for project creation

#     Attributes:
#         specification (str, optional): same as class name
#         version (int, optional): project version
#         teams (dict, optional): Github teams; name, permission pairs
#         gitignore (list, optional): gitignore patterns
#         lfs_extensions (list, optional): lfs tracked file extensions
#         nondeliverables (list, optional): nondeliverable asset specs/patterns
#         deliverables (list, optional): deliverable asset specs/patterns
#         private (bool, optional): privacy of Github repo
#     '''
#     version         = IntType(validators=[is_version])
#     teams           = DictType(StringType, validators=[is_teams])
#     gitignore       = ListType(StringType, validators=[])
#     lfs_extensions  = ListType(StringType, validators=[is_extension, is_not_empty])
#     nondeliverables = ListType(StringType, validators=[])
#     deliverables    = ListType(StringType, validators=[is_specification])
#     private         = BooleanType(validators=[is_private])

# class Project(Specification):
#     '''
#     Base class for all nerve projects

#     Attributes:
#         specification (str): same as class name
#         project_name (str): name of project
#         project_id (str): Github repo id
#         project_url (str): project_url of project's Github repo
#         notes (str): project notes
#         private (bool): privacy of Github repo
#         version (int): project version
#         teams (dict): Github teams; name, permission pairs
#         gitignore (list): gitignore patterns
#         lfs_extensions (list): lfs tracked file extensions
#         nondeliverables (list, optional): nondeliverable asset specs/patterns
#         deliverables (list): deliverable asset specs/patterns
#     '''
#     project_name    = StringType(required=True, validators=[is_project_name])
#     project_id      = StringType(required=True, validators=[is_project_id])
#     project_url     = StringType(required=True, validators=[is_project_url])
#     notes           = StringType(default='')

#     private         = BooleanType(required=True, validators=[is_private])
#     version         = IntType(required=True, validators=[is_version])
#     teams           = DictType(StringType, required=True, validators=[is_teams])
#     gitignore       = ListType(StringType, required=True, validators=[])
#     lfs_extensions  = ListType(StringType, required=True, validators=[is_extension, is_not_empty])
#     nondeliverables = ListType(StringType, default=[], validators=[])
#     deliverables    = ListType(StringType, required=True, validators=[is_specification])

# class Asset(Specification):
#     '''
#     Base class for Deliverable and NonDeliverable

#     Attributes:
#         specification (str): same as class name
#         project_name (str): name of project
#         project_id (str): Github repo id
#         project_url (str): project_url of project's Github repo
#         notes (str): project notes
#         asset_name (str): name of asset
#         asset_id (str): randomly generated uuid
#         data (list): list of filepaths
#     '''
#     project_name = StringType(required=True, validators=[is_project_name])
#     project_id   = StringType(required=True, validators=[is_project_id])
#     project_url  = StringType(required=True, validators=[is_project_url])
#     notes        = StringType(default='')

#     asset_name   = StringType(required=True, validators=[])
#     asset_id     = StringType(required=True, validators=[is_asset_id])
#     data         = ListType(StringType, validators=[is_file, is_path, is_exists])

# class NonDeliverable(Asset):
#     '''
#     Base class for all nerve non-deliverable assets

#     Attributes:
#         specification (str): same as class name
#         project_name (str): name of project
#         project_id (str): Github repo id
#         project_url (str): project_url of project's Github repo
#         notes (str): project notes
#         asset_name (str): name of asset
#         asset_id (str): randomly generated uuid
#         data (list): list of filepaths
#         asset_type (str): 'nondeliverable'
#     '''
#     asset_type   = StringType(default='nondeliverable')

# class Deliverable(Asset):
#     '''
#     Base class for all nerve deliverable assets

#     Attributes:
#         specification (str): same as class name
#         project_name (str): name of project
#         project_id (str): Github repo id
#         project_url (str): project_url of project's Github repo
#         notes (str): project notes
#         asset_name (str): name of asset
#         asset_id (str): randomly generated uuid
#         data (list): list of filepaths
#         descriptor (str): descriptor found in asset name
#         version (int): version found in asset name
#         dependencies (list): deliverables asset depends upon. Default: []
#         asset_type (str): 'deliverable'
#     '''
#     descriptor   = StringType(required=True, validators=[is_descriptor])
#     version      = IntType(required=True, validators=[is_version])
#     dependencies = ListType(StringType, default=[])
#     asset_type   = StringType(default='deliverable')

# class Config(Specification):
#     '''
#     Base class for all nerve configs (nerverc)

#     Attributes:
#         specification (str): same as class name
#         username (str): Github username
#         user_branch (str): User's branch name
#         organization (str): Github organization
#         project_root (str): fullpath to root projects directory
#         token (str): Github oauth token
#         private (bool): privacy of Github repo
#         url_type (str): type of access to Github. currently only ssh. Options: http, ssh
#         request_include_patterns (list, optional): regular expressions used to include assets within a request
#             Default: []
#         request_exclude_patterns (list, optional): regular expressions used to exclude assets within a request
#             Default: []
#         publish_include_patterns (list, optional): regular expressions used to include assets within a publish
#             Default: []
#         publish_exclude_patterns (list, optional): regular expressions used to exclude assets within a publish
#             Default: []
#         status_include_patterns (list, optional): regular expressions used to include assets within a status call
#             Default: []
#         status_exclude_patterns (list, optional): regular expressions used to exclude assets within a status call
#             Default: []
#         status_states (list, optional): list of allowed states for status call
#             Default: []. Options: added, copied, deleted, modified, renamed, updated, untracked
#         status_asset_types (list, optional): list of allowed asset types for status call
#             Default: []. Options: deliverable, nondeliverable
#         log_level (str, optional): level of logging. Default: warn
#         environment (dict): Environment variables
#         lfs_server_url (str, optional): url of lfs server. Default: http://localhost:8080
#         git_credentials (list): list of git credentials
#         timeout (int, optional): maximum timeout in seconds. Default: 100
#         project_template (dict, optional): project specification
#     '''
#     username                 = StringType(required=True, validators=[is_username])
#     user_branch              = StringType(required=True, validators=[is_user_branch])
#     organization             = StringType(required=True, validators=[is_organization])
#     project_root             = StringType(required=True, validators=[is_project_root])
#     token                    = StringType(required=True, validators=[is_token])
#     url_type                 = StringType(required=True, validators=[is_url_type])
#     request_include_patterns = ListType(StringType, default=[], validators=[is_include_pattern])
#     request_exclude_patterns = ListType(StringType, default=[], validators=[is_exclude_pattern])
#     publish_include_patterns = ListType(StringType, default=[], validators=[is_include_pattern])
#     publish_exclude_patterns = ListType(StringType, default=[], validators=[is_exclude_pattern])
#     status_include_patterns  = ListType(StringType, default=[], validators=[is_include_pattern])
#     status_exclude_patterns  = ListType(StringType, default=[], validators=[is_exclude_pattern])
#     status_states            = ListType(StringType, default=[], validators=[is_status_state])
#     status_asset_types       = ListType(StringType, default=[], validators=[is_status_asset_type])
#     log_level                = StringType(default='warn')
#     environment              = DictType(StringType, required=True, validators=[])
#     lfs_server_url           = URLType(default='http://localhost:8080', required=True)
#     git_credentials          = ListType(StringType, required=True)
#     timeout                  = IntType(default=100, required=True)
#     project_template         = StringType(validators=[is_exists])
#     private                  = BooleanType(required=True, validators=[is_private])

#     def validate_project(self, key, data):
#         '''
#         Validates project metadata

#         Args:
#             key (None): does nothing
#             data (dict): project metadata

#         Returns:
#             None
#         '''
#         is_specification(data['specification'])
