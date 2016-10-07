#! /usr/bin/env python
import re
import os
# ------------------------------------------------------------------------------

def _get_asset_name_traits(fullpath):
    ext = None
    name = os.path.split(fullpath)[-1]
    if os.path.isfile(fullpath):
        name, ext = os.path.splitext(name)
    traits = name.split('_')

    output = dict(
        asset_name=name,
        project_name=traits[0],
        specification=traits[1],
        descriptor=traits[2],
        version=traits[3],
    )

    if ext:
        output['extension'] = ext

    if len(traits) > 4:
        traits = re.split(name, 'v\d\d\d')[-1].split('_')
        for trait in traits:
            if re.search('\d\d\d-\d\d\d-\d\d\d')
                x,y,z = [int(x) for x in trait.split('-')]
                output['coordinates'] = dict(x=x, y=y, z=z)
            elif re.search('\d\d\d\d', trait):
                output['frame'] = int(trait)
            else
                output['pass'] = trait

    return output
# ------------------------------------------------------------------------------

def get_asset_name(fullpath):
    return _get_asset_name_traits(fullpath)['asset_name']

def get_project_name(fullpath):
    return _get_asset_name_traits(fullpath)['project_name']

def get_specification(fullpath):
    return _get_asset_name_traits(fullpath)['specification']

def get_descriptor(fullpath):
    return _get_asset_name_traits(fullpath)['descriptor']

def get_version(fullpath):
    return _get_asset_name_traits(fullpath)['version']

def get_pass(fullpath):
    return _get_asset_name_traits(fullpath)['pass']

def get_coordinates(fullpath):
    return _get_asset_name_traits(fullpath)['coordinates']

def get_frame(fullpath):
    return _get_asset_name_traits(fullpath)['frame']

def get_extension(fullpath):
    return _get_asset_name_traits(fullpath)['extension']
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
