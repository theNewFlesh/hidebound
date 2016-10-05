#! /usr/bin/env python
# ------------------------------------------------------------------------------

def get_asset_name(fullpath):
    return 'asset-name', os.path.split(fullpath)[-1]
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
