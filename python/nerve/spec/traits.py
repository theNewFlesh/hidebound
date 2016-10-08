#! /usr/bin/env python
import re
import os
from collections import defaultdict
from nerve.core.utils import get_asset_name_traits
# ------------------------------------------------------------------------------

def get_asset_name(fullpath):
    return get_asset_name_traits(fullpath)['asset_name']

def get_project_name(fullpath):
    return get_asset_name_traits(fullpath)['project_name']

def get_specification(fullpath):
    return get_asset_name_traits(fullpath)['specification']

def get_descriptor(fullpath):
    return get_asset_name_traits(fullpath)['descriptor']

def get_version(fullpath):
    return get_asset_name_traits(fullpath)['version']

def get_render_pass(fullpath):
    return get_asset_name_traits(fullpath)['render_pass']

def get_extension(fullpath):
    return get_asset_name_traits(fullpath)['extension']

def get_coordinates(fullpath):
    if os.path.isdir(fullpath):
        output = defaultdict(lambda: [])
        for file_ in os.listdir(fullpath):
            temp = get_asset_name_traits(fullpath)
            if temp.has_key('coordinates'):
                for key, val in temp['coordinates']:
                    output[key].append(val)
        return dict(output)

def get_frames(fullpath):
    if os.path.isdir(fullpath):
        output = []
        for file_ in os.listdir(fullpath):
            temp = get_asset_name_traits(fullpath)
            if temp.has_key('frame'):
                output.append(temp['frame'])
        return output
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
