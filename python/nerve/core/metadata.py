#! /usr/bin/env python
'''
The metadata module contain the Metadata class which is used by nerve to handle all metadata
'''
# ------------------------------------------------------------------------------

import os
from pprint import pformat
import yaml
from nerve.core.utils import conform_keys, deep_update
from nerve.spec.base import MetaName
from nerve.spec import specifications, traits
from nerve.core.errors import SpecificationError
# ------------------------------------------------------------------------------

class Metadata(object):
    '''
    The Metadata class provides a simple object for generating, validating and writing metadata

    Internally, Metadata generates a specification class found in the specifications module.
    Those specification classes are themselves subclassed from schematics.model.Model.

    API: data, get_traits, validate, write, __getitem__

    Constructor takes a dict, filepath or dirpath and turns it into internal metadata
    The specification class used to wrap the internal data is derived from item.

    Args:
        item (dict or str): a dict of asset metadata, an asset yml file or
                            the fullpath of an asset
        metapath (str, optional): fullpath to item metadata _meta.yml file. Default: None
        datapath (str, optional): fullpath to item data. Default: None
        spec (str, optional): item specification. Default: None

    Returns:
        Metadata

    Raises:
        OSError, TypeError
    '''
    def __init__(self, item, metapath=None, datapath=None, spec=None, skip_keys=[]):
        data = {}

        if isinstance(item, dict):
            spec = item['specification']
            data = item

        elif isinstance(item, str):
            if not os.path.exists(item):
                raise OSError('No such file or directory: ' + item)

            meta = traits.get_meta(item)
            conf = traits.get_config(item)
            if meta:
                spec = traits.get_specification(item)
            if meta or conf:
                metapath = item
                with open(item, 'r') as f:
                    data = yaml.load(f)

            else:
                datapath = item
                metapath = os.path.splitext(item)[0] + '_meta.yml'
                spec = traits.get_specification(item)

        else:
            raise TypeError('type: ' + type(item) + ' not supported')

        spec = self._get_spec(spec)
        self._data = spec(data)
        self._datapath = datapath
        self._metapath = metapath
        self._skip_keys = skip_keys

    def __repr__(self):
        return pformat(self.data)

    def __getitem__(self, key):
        return self.data[key]

    def _get_spec(self, name):
        '''
        Convenience method that returns a class from the specifications module of the same name

        Args:
            name (str): specification class name (all lowercase is fine)

        Returns:
            Specification: specification of class "name"
        '''
        name = name.capitalize()
        if hasattr(specifications, name):
            return getattr(specifications, name)
        else:
            msg = '"' + name + '" specification not found in specifications module'
            raise SpecificationError(msg)

    @property
    def metapath(self):
        '''
        str: fullpath to _meta file
        '''
        return self._metapath

    @property
    def datapath(self):
        '''
        str: fullpath to data
        '''
        return self._datapath
    # --------------------------------------------------------------------------

    def get_traits(self):
        '''
        Generates metadata from evaluating data files pointed to provided metadata
        Uses trait function from the traits module to overwrites internal data
        with new values

        Args:
            None

        Returns:
            dict: traits
        '''
        output = {}
        for key in self._data.keys():
            trait = 'get_' + key
            if hasattr(traits, trait):
                trait = getattr(traits, trait)
                output[key] = trait(self._datapath)

        self._data.import_data(output)
        return output

    @property
    def data(self):
        '''
        dict: copy of internal data
        '''
        output = self._data.to_primitive()
        return conform_keys(output, skip=self._skip_keys)

    def validate(self):
        '''
        Validates internal data accodring to specification

        Args:
            None

        Return:
            bool: validity
        '''
        return self._data.validate() is None

    def write(self, fullpath=None, validate=True):
        '''
        Writes internal data to file with correct name in correct location

        Args:
            fullpath (str, optional): full path to yml metadata file

        Returns:
            bool: success status
        '''
        if not fullpath:
            fullpath = self._metapath

        if validate:
            meta = traits.get_name_traits(fullpath)
            MetaName(meta).validate()

        # overwrite existing metadata
        data = {}
        if os.path.exists(fullpath):
            with open(fullpath, 'r') as f:
                data = yaml.load(f)
        data = deep_update(data, self._data.to_primitive())

        with open(fullpath, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)

        return os.path.exists(fullpath)
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

__all__ = ['Metadata']

if __name__ == '__main__':
    main()
