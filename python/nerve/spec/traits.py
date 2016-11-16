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
# ------------------------------------------------------------------------------

def fetch_name_traits(fullpath, deliverable=True):
    '''
    Given an asset directory or file return a dict of traits derived from the name

    A traits utility function, not a bonified trait.

    Args:
        fullpath (str): full path to file or directory

    Returns:
        dict: traits
              (project_name, specification, descriptor, version,
               extension, render_pass, coordinates, frame)
    '''
    name = os.path.split(fullpath)[-1]
    # skip hidden files
    if name[0] == '.':
        return {}

    ext = None
    if re.search('\.[a-zA-Z0-9]+$', name):
        name, ext = os.path.splitext(name)
        ext = ext[1:]
    traits = name.split('_')

    output = dict(
        project_name=traits[0],
        specification=traits[1]
    )
    if deliverable:
        output = dict(
            project_name=traits[0],
            specification=traits[1],
            descriptor=traits[2],
            version=int(traits[3][1:]),
            render_pass=traits[4],
            coordinate=None,
            frame=None,
            extension=ext
        )

        if re.search('\d\d\d-\d\d\d(-\d\d\d)?', traits[5]):
            vals = traits[5].split('-')
            keys = list('xyz')[:len(vals)]
            vals = {k:int(v) for k,v in zip(keys, vals)}
            output['coordinate'] = vals

        if re.search('\d\d\d\d', traits[6]):
            output['frame'] = int(traits[6])

        if re.search('_meta', name):
            output['meta'] = True

    for k,v in output.items():
        if v == '-':
            output[k] = None
    return output

def fetch_project_traits(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        str: project metadata
    '''
    project = fullpath.split(os.sep)[:-2]
    project = os.path.join(os.sep, *project)
    files = os.listdir(project)
    files = filter(lambda x: re.search('.+_[a-z]+\d\d\d_meta\.yml', x), files)
    files = list(files)
    if len(files) > 0:
        meta = os.path.join(project, files[0])
        with open(meta, 'r') as f:
            meta = yaml.load(f)
            return meta
    return None
# ------------------------------------------------------------------------------

def get_meta(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        bool: is metadata file
    '''
    if re.search('_meta', fullpath):
        return True
    return False

def get_config(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        bool: is nerverc file
    '''
    if re.search('nerverc', fullpath):
        return True
    return False

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
    return fetch_name_traits(fullpath, False)['project_name']

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
    return fetch_name_traits(fullpath, False)['specification']

def get_descriptor(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        str: descriptor
    '''
    return fetch_name_traits(fullpath)['descriptor']

def get_version(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        str: version
    '''
    return fetch_name_traits(fullpath)['version']

def get_render_pass(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        str: render pass
    '''
    return fetch_name_traits(fullpath)['render_pass']

def get_coordinates(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        dict: x,y or x,y,z coordinates
    '''
    if os.path.isdir(fullpath):
        output = defaultdict(lambda: [])
        for file_ in os.listdir(fullpath):
            coord = fetch_name_traits(file_)['coordinate']
            for key, val in coord.items():
                output[key].append(val)
        return dict(output)
    return fetch_name_traits(fullpath)['coordinate']

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
            frame = fetch_name_traits(file_)['frame']
            output.append(frame)
        return output
    return fetch_name_traits(fullpath)['frame']

def get_extension(fullpath):
    '''
    Args:
        fullpath (str): absolute file path

    Returns:
        str: file extension
    '''
    return fetch_name_traits(fullpath)['extension']

def get_template(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        bool: is nerverc template file
    '''
    if re.search('nerverc_temp', fullpath):
        return True
    return False
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
