#! /usr/bin/env python
'''
The specifications module house all the specifications for nerve entities

Those entities include: configs, projects, assets (non-deliverables) and
deliverables.

All specifications used in production should be subclassed from the
aforementioned classes.  All class attributes must have a "get_[attribute]"
function in the traits module and should have one or more validators related t
the value of that trait (especially if required).
'''
# ------------------------------------------------------------------------------

from nerve.spec.base import Config, Project, Deliverable, NonDeliverable, Client
# ------------------------------------------------------------------------------

class Config001(Config):
    pass

class Proj001(Project):
    pass

class Vol001(Deliverable):
    pass

class Geo001(Deliverable):
    pass

class Maya001(NonDeliverable):
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
    'Config001',
    'Proj001',
    'Vol001',
    'Geo001',
    'Maya001'
]

if __name__ == '__main__':
    main()
