#! /usr/bin/env python
import os
import re
import yaml
from itertools import *
from warnings import warn
from nerve.spec import specifications as specs
# ------------------------------------------------------------------------------

class Metadata(object):
    def __init__(self, fullpath):
        if not os.path.exists(fullpath):
            raise OSError('No such file or directory: ' + fullpath)
        if ext in ['yml', 'yaml']:
            with open(fullpath, 'r') as f:
                self._data = yaml.load(f)
        else:
            self._data = self.generate_metadata(fullpath)

    def __getitem__(self, key):
        return self._data[key]

    def generate_metadata(self, fullpath):
        root, name = os.path.split(fullpath)
        root, spec = os.path.split(root)
        data = {}
        spec = specs.getattr(spec)

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
