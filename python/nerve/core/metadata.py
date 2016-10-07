#! /usr/bin/env python
import os
import re
import yaml
from itertools import *
from warnings import warn
from nerve.spec import specifications
from nerve.core.errors import SpecificationError
# ------------------------------------------------------------------------------

class Metadata(object):
    def __init__(self, item):
        spec = None
        if isinstance(item, dict):
            spec = item['specification']

        elif isinstance(item, str):
            if not os.path.exists(item):
                raise OSError('No such file or directory: ' + item)

            spec = os.path.split(item)[0]
            spec = os.path.split(spec)[-1]

            if ext in ['yml', 'yaml']:
                self._metapath = item
                with open(item, 'r') as f:
                    item = yaml.load(f)

            else:
                self._datapath = item
                item = dict(
                    specification=spec
                )

        else:
            raise TypeError('type: ' + type(item) + ' not supported')

        spec = self.get_spec(spec)
        self._data = spec(item)

    def __getitem__(self, key):
        return self._data[key]
    # --------------------------------------------------------------------------

    def get_spec(self, name):
        if hasattr(specifications, name.capitalize()):
            return getattr(specifications, name)
        else:
            raise SpecificationError(name + ' specification not found in specifications module')

    def get_traits(self):
        '''
        finds traits for file(s) and overwrites internal data with them
        '''
        traits = {}
        for key in self._data.keys():
            trait = 'get_' + key
            if hasattr(traits, trait):
                trait = getattr(traits, trait)
                trait[key] = trait(self._datapath)

        self._data.import_data(traits)

    @property
    def data(self):
        output = self._data.to_primitive()
        return {re.sub('_', '-', k): v for k,v in output.items()}

    def validate(self):
        return assert(self._data.validate() == None)

    def write(self):
        with open(self._metapath, 'w') as f:
            yaml.dump(self._data.to_primitive(), f)
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
