#! /usr/bin/env python
import re
import os
from collections import defaultdict
# ------------------------------------------------------------------------------

def get_name_traits(fullpath):
    '''
    Given an asset directory or file return a dict of traits derived from the name

    Args:
        fullpath (str): full path to file or directory

    Returns:
        dict: traits
              (asset_name, project_name, specification, descriptor, version,
               extension, coordinates, frame, render_pass, metadata)
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
        asset_name=name,
        project_name=traits[0],
        specification=traits[1],
        descriptor=traits[2],
        version=int(traits[3][1:]),
        render_pass=traits[4],
        coordinate=None,
        frame=None,
        extension=ext,
        meta=False
    )

    if re.search('\d\d\d-\d\d\d(-\d\d\d)?', traits[5]):
        vals = traits[5].split('-')
        keys = list('xyz')[:len(vals)]
        vals = {k:int(v) for k,v in zip(keys, vals)}
        output['coordinate'] = vals

    if re.search('\d\d\d\d', traits[6]):
        output['frame'] = int(traits[6])

    if re.search('_meta$', name):
        output['meta'] = True

    for k,v in output.items():
        if v == '-':
            output[k] = None
    return output
# ------------------------------------------------------------------------------

def get_asset_name(fullpath):
    return get_name_traits(fullpath)['asset_name']

def get_project_name(fullpath):
    return get_name_traits(fullpath)['project_name']

def get_specification(fullpath):
    return get_name_traits(fullpath)['specification']

def get_descriptor(fullpath):
    return get_name_traits(fullpath)['descriptor']

def get_version(fullpath):
    return get_name_traits(fullpath)['version']

def get_render_pass(fullpath):
    return get_name_traits(fullpath)['render_pass']

def get_coordinates(fullpath):
    if os.path.isdir(fullpath):
        output = defaultdict(lambda: [])
        for file_ in os.listdir(fullpath):
            coord = get_name_traits(file_)['coordinate']
            for key, val in coord.items():
                output[key].append(val)
        return dict(output)
    return get_name_traits(fullpath)['coordinate']

def get_frames(fullpath):
    if os.path.isdir(fullpath):
        output = []
        for file_ in os.listdir(fullpath):
            frame = get_name_traits(file_)['frame']
            output.append(frame)
        return output
    return get_name_traits(fullpath)['frame']

def get_extension(fullpath):
    return get_name_traits(fullpath)['extension']

def get_meta(fullpath):
    return get_name_traits(fullpath)['meta']
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
