#! /usr/bin/env python
from schematics.exceptions import ValidationError
# ------------------------------------------------------------------------------

def is_metadata(item):
    if item == '_meta':
        return True
    raise ValidationError('_meta not found in ' + str(item))

def is_asset_id(item):
    return True

def is_asset_name(item):
    return True

def is_assets(item):
    return True

def is_data(item):
    return True

def is_deliverables(item):
    return True

def is_extensions(item):
    return True

def is_gitignore(item):
    return True

def is_organization(item):
    return True

def is_private(item):
    return True

def is_project_id(item):
    return True

def is_project_name(item):
    return True

def is_project_root(item):
    return True

def is_publish_exclude_patterns(item):
    return True

def is_publish_include_patterns(item):
    return True

def is_request_exclude_patterns(item):
    return True

def is_request_include_patterns(item):
    return True

def is_specification(item):
    return True

def is_teams(item):
    return True

def is_token(item):
    return True

def is_url(item):
    return True

def is_url_type(item):
    return True

def is_user_branch(item):
    return True

def is_username(item):
    return True

def is_version(item):
    return True

def is_render_pass(item):
    return True

def is_frames(item):
    return True

def is_coordinates(item):
    return True
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
