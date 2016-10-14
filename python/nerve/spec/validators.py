#! /usr/bin/env python
'''
The validators module is function library for validating singular traits given to a specification

Much like the traits module, validator functions follow a "is_"[trait] naming
convention.  Validators are linked with traits inside the validators kwarg of a
specification class attribute in the specifications module.  They succeed
silently and raise ValidationError when the trait they validate fails.
Schematics captures these error messages and pipes them to a error call.

Functions should generally be wrapped with the is_a or is_re decorators for
brevity.
'''
# ------------------------------------------------------------------------------

import os
import re
from functools import wraps
from schematics.exceptions import ValidationError
import nerve
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

def is_deliverable_name(items):
    proj  = '[a-z]+\d\d\d'
    spec  = '[a-z]+\d\d\d'
    desc  = '[-a-zA-Z0-9]'
    ver   = 'v\d\d\d'
    rpass = '([-a-z0-9]+|-)'
    coord = '(\d\d\d-\d\d\d-\d\d\d|-)'
    frame = '(\d\d\d\d|-)'
    ext   = '(\.[a-zA-Z0-9]+|)'
    regex = '_'.join([proj, spec, desc, ver, rpass, coord, frame, ext])
    regex = '^' + regex + '$'
    regex = re.compile(regex)

    if isinstance(items, str):
        items = [items]

    for item in items:
        if regex.search(item):
            continue
        raise ValidationError(str(item) + ' is not a valid deliverable name')
    return True

@is_re('[-a-z0-9]+', 'is not a valid descriptor')
def is_descriptor(item): return

@is_re('[a-zA-Z0-9]+', 'is not a valid extension')
def is_extension(item): return

@is_a(lambda x: x <= 9999, 'is not a valid frame')
def is_frame(item): return

# @is_re('[.*/a-zA-Z0-9_]+', 'is not a valid gitignore pattern')
# def is_gitignore(item): return

@is_a(lambda x: x, 'does not contain _meta in name')
def is_meta(item): return

@is_a(lambda x: x in ['yml', 'yaml'], 'is not a valid metadata extension')
def is_metadata_extension(item): return

def is_metapath(item):
    meta = nerve.spec.traits.get_name_traits(item)
    nerve.spec.specifications.MetaName(meta).validate()
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

@is_re('$|^'.join([
        'beauty',
        'specular',
        'diffuse',
        'shadow',
        'ambient-occlusion',
        'world-point-position',
        'uv',
        'normal',
        'depth',
        'z',
        'matte'
    ]),
    'is not a valid render pass'
)
def is_render_pass(item): return

def is_request_exclude_patterns(item):
    return True

def is_request_include_patterns(item):
    return True

@is_a(
    lambda x: hasattr(nerve.spec.specifications, x.capitalize()),
    'is not a valid specification')
def is_specification(item): return

@is_re('added|copied|deleted|modified|renamed|updated|untracked',
    'is not a valid state')
def is_status_state(item): return

@is_re('nondeliverable|deliverable', 'is not a valid asset type')
def is_status_asset_type(item): return

def is_teams(item):
    return True

def is_token(item):
    return True

def is_url(item):
    return True

@is_re('ssh$|^http', 'is not ssh or http')
def is_url_type(item): return

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
