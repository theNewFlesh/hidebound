#! /usr/bin/env python
import os
import re
import yaml
from itertools import *
from warnings import warn
# ------------------------------------------------------------------------------

class Metadata(object):
    def __init__(self, fullpath):
        pass

    def write(self):
        pass

    @property
    def deliverable(self):
        pass

    @property
    def valid(self):
        pass
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
