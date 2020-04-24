#! /usr/bin/env python
'''
The traits module is function library for specifying singular facts about given files

All trait functions begin with "get_" and then the trait name.  Traits must are
names exactly the same as their class attribute counterparts in teh specifications
module.  Triats may only return primitive datatypes.
'''
# ------------------------------------------------------------------------------

import re
import os
from collections import defaultdict
from uuid import uuid4
import yaml
from nerve.core.utils import Name, fetch_project_traits
# ------------------------------------------------------------------------------

def get_meta(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        bool: is metadata file
    '''
    return Name(fullpath).meta

def get_config(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        bool: is nerverc file
    '''
    return Name(fullpath).config

def get_asset_id(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        str: uuid
    '''
    return str(uuid4())

def get_asset_name(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path
    '''
    output = os.path.split(fullpath)[-1]
    return os.path.splitext(output)[0]

def get_project_name(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        str: project name
    '''
    return Name(fullpath).project_name

def get_project_id(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        str: project id
    '''
    meta = fetch_project_traits(fullpath)
    if meta:
        return meta['project_id']
    return None

def get_project_url(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        str: github url
    '''
    meta = fetch_project_traits(fullpath)
    if meta:
        return meta['project_url']
    return None

def get_specification(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        str: asset specification
    '''
    return Name(fullpath).specification

def get_descriptor(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        str: descriptor
    '''
    return Name(fullpath).descriptor

def get_version(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        str: version
    '''
    return Name(fullpath).version

def get_render_pass(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        str: render pass
    '''
    return Name(fullpath).render_pass

def get_coordinates(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        dict: x,y or x,y,z coordinates
    '''
    if os.path.isdir(fullpath):
        output = []
        for file_ in os.listdir(fullpath):
            coord = Name(file_).coordinate
            output.append(coord)
        return output
    return [Name(fullpath).coordinate]

def get_frames(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        list(int): frames
    '''
    if os.path.isdir(fullpath):
        output = []
        for file_ in os.listdir(fullpath):
            frame = Name(file_).frame
            output.append(frame)
        return output
    return [Name(fullpath).frame]

def get_extension(fullpath):
    '''
    Args:
        fullpath (str): absolute file path

    Returns:
        str: file extension
    '''
    return Name(fullpath).extension

def get_template(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        bool: is nerverc template file
    '''
    return Name(fullpath).template
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
