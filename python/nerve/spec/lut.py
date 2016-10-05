#! /usr/bin/env python
from nerve.spec.traits import *
# ------------------------------------------------------------------------------

LUT = dict(
    vol001=[
        get_asset_name
    ]
)
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

__all__ = ['LUT']

if __name__ == '__main__':
    main()
