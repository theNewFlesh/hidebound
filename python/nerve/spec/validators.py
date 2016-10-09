#! /usr/bin/env python
import os
import re
from functools import wraps
from schematics.exceptions import ValidationError
# ------------------------------------------------------------------------------

def is_a(predicate=lambda x: x != None, message=''):
    def decorator(func):
        @wraps(func)
        def wrapper(items):

            if isinstance(items, dict):
                items = items.items()
            elif items.__class__.__name__ not in ['list', 'tuple']:
                items = [items]

            for item in items:
                if predicate(item):
                    if func(item) == None:
                        continue
                raise ValidationError(str(item) + ' ' + message)
            return True

        return wrapper
    return decorator

def is_re(regex, message=''):
    return is_a(lambda x: re.search('^' + regex + '$', x), message)
# ------------------------------------------------------------------------------

@is_a(os.path.exists, 'does not exist')
def is_exists(item): return

@is_a(os.path.isabs, 'is not a valid fullpath')
def is_path(item): return

@is_a(os.path.isfile, 'is not a valid file path')
def is_file(item): return

@is_a(os.path.isdir, 'is not a valid directory path')
def is_directory(item): return
# ------------------------------------------------------------------------------

def is_asset_id(item):return True

@is_a(lambda x: x[0] in list('xyz'), 'is not a valid coordinate')
def is_coordinate(item): return

@is_re('[-a-z0-9]+', 'is not a valid descriptor')
def is_descriptor(item): return

@is_re('[a-zA-Z0-9]+', 'is not a valid extension')
def is_extension(item): return

@is_a(lambda x: x <= 9999, 'is not a valid frame')
def is_frame(item): return

# @is_re('[.*/a-zA-Z0-9_]+', 'is not a valid gitignore pattern')
# def is_gitignore(item): return

@is_a(lambda x: x == '_meta', 'does not contain _meta in name')
def is_metadata(item): return

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

def is_render_pass(item):
    return True

def is_request_exclude_patterns(item):
    return True

def is_request_include_patterns(item):
    return True

@is_re('[a-z]+\d\d\d', 'is not a valid specification')
def is_specification(item): return

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
