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
    def __init__(self, data, spec):
        if isinstance(data, dict):
            pass
        elif isinstance(data, str):
            if not os.path.exists(data):
                raise OSError('No such file or directory: ' + data)
            if ext in ['yml', 'yaml']:
                with open(data, 'r') as f:
                    data = yaml.load(f)
            else:
                data = self.generate_metadata(data)
        else:
            raise TypeError('type: ' + type(data) + ' not supported')

        spec = self.get_spec(spec)
        self._data = spec(data)

    def get_spec(self, name):
        if hasattr(specifications, name.capitalize()):
            return getattr(specifications, name)
        else:
            raise SpecificationError(name + ' specification not found in nerve.spec.specifications')

    def __getitem__(self, key):
        return self._data[key]

    def generate_metadata(self, fullpath):
        root, name = os.path.split(fullpath)
        root, spec = os.path.split(root)
        data = {}
        spec = specifications.getattr(spec)

        return data

    @property
    def data(self):
        return self._data

    @property
    def deliverable(self):
        return self._data['deliverable']

    @property
    def valid(self):
        output = False
        # use schematics to verify or falsify
        return output

    def write(self):
        with open(self._metapath, 'w') as f:
            yaml.dump(self._data, f)
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
