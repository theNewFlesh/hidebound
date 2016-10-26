#! /usr/bin/env python
'''
The errors module contains custom nerve errors
'''
# ------------------------------------------------------------------------------

class SpecificationError(Exception):
    '''
    Error used for missing specifications
    '''
    pass

class KeywordError(Exception):
    '''
    Error used for invalid keywords
    '''
    pass

class TimeoutError(Exception):
    '''Error used for server call timeouts'''
    pass
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

__all__ = [
    'SpecificationError',
    'KeywordError',
    'TimeoutError'
]

if __name__ == '__main__':
    main()
