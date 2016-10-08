#! /usr/bin/env python
from schematics.exceptions import ValidationError
# ------------------------------------------------------------------------------

def is_metadata(item):
    if item != 'metadata':
        raise ValidationError('_meta not found in file name')
    return True

def is_asset_id(item):
    pass

def is_asset_name(item):
    pass

def is_assets(item):
    pass

def is_data(item):
    pass

def is_deliverables(item):
    pass

def is_extensions(item):
    pass

def is_gitignore(item):
    pass

def is_organization(item):
    pass

def is_private(item):
    pass

def is_project_id(item):
    pass

def is_project_name(item):
    pass

def is_project_root(item):
    pass

def is_publish_exclude_patterns(item):
    pass

def is_publish_include_patterns(item):
    pass

def is_request_exclude_patterns(item):
    pass

def is_request_include_patterns(item):
    pass

def is_specification(item):
    pass

def is_teams(item):
    pass

def is_token(item):
    pass

def is_url(item):
    pass

def is_url_type(item):
    pass

def is_user_branch(item):
    pass

def is_username(item):
    pass

def is_version(item):
    pass

def is_render_pass(item):
    pass

def is_frames(item):
    pass

def is_coordinates(item):
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
