#! /usr/bin/env python
'''
The api module contains the User and Admin classes, which wrap the nerve model class

Platforrm:
    Unix

Author:
    Alex Braun <alexander.g.braun@gmail.com> <http://www.alexgbraun.com>
'''
# ------------------------------------------------------------------------------

import os
import re
from warnings import warn
from nerve.core.model import Nerve
from nerve.core.metadata import Metadata
# ------------------------------------------------------------------------------

class NerveUser(object):
    def __init__(self):
        with open('/etc/nerve/config-location.txt', 'r') as f:
            self._nerve = Nerve(f.read().strip('\n'))

    def __getitem__(self, key):
        return self._nerve.__getitem__(key)

    def __repr__(self):
        return self._nerve.__repr__()

    def _get_project(self):
        cwd = os.getcwd()
        files = os.listdir(cwd)
        if '.git' in files:
            meta = list(filter(lambda x: re.search('_meta.yml', x), files))
            if len(meta) > 0:
                meta = meta[0]
                meta = os.path.join(cwd, meta)
                meta = Metadata(meta)
                if re.search('proj\d\d\d', meta['specification']):
                    return meta.data
        warn('project metadata not found')
        return False

    def status(self, **config):
        project = self._get_project()
        if not project:
            return project
        config['project'] = project
        return self._nerve.status(**config)

    def clone(self, name=None, **config):
        return self._nerve.clone(name, **config)

    def request(self, **config):
        project = self._get_project()
        if not project:
            return project
        config['project'] = project
        return self._nerve.request(**config)

    def publish(self, notes=None, **config):
        project = self._get_project()
        if not project:
            return project
        config['project'] = project
        return self._nerve.publish(notes=notes, **config)

    def delete(self, project=None):
        if project == None:
            project = self._get_project()
            if not project:
                return project
        return self._nerve.delete(False, True, project=project)
# ------------------------------------------------------------------------------

class NerveAdmin(NerveUser):
    def __init__(self):
        super().__init__()

    def create(self, name, notes=None, **config):
        return self._nerve.create(name, notes, **config)

    def delete(self, from_server, from_local, project=None):
        if project == None:
            project = self._get_project()
            if not project:
                return project
        return self._nerve.delete(from_server, from_local, project=project)
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

__all__ = ['NerveUser', 'NerveAdmin']

if __name__ == '__main__':
    main()
