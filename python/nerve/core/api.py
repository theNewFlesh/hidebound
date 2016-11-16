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
    '''
    Class for interacting with nerve as a user

    Args:
        None

    Returns:
        Client: NerveUser
    '''
    def __init__(self):
        with open('/etc/nerve/config-location.txt', 'r') as f:
            self._nerve = Nerve(f.read().strip('\n'))

    def __getitem__(self, key):
        return self._nerve.__getitem__(key)

    def __repr__(self):
        return self._nerve.__repr__()

    def _get_project(self):
        '''
        Finds and returns project metadata

        Args:
            None

        Returns:
            dict: Metadata
        '''
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
        r'''
        Reports on the status of all affected files within a given project

        Args:
            \**config: optional config parameters, overwrites fields in a copy of self.config
            status_include_patterns (list, \**config): list of regular expressions user to include specific assets
            status_exclude_patterns (list, \**config): list of regular expressions user to exclude specific assets
            status_states (list, \**config): list of object states files are allowed to be in.
                Options: added, copied, deleted, modified, renamed, updated and untracked
            verbosity (int, \**config): level of verbosity for output. Default: 0
                Options: 0, 1, 2

        Yields:
            Metadata: Metadata object of each asset
        '''
        project = self._get_project()
        if not project:
            return project
        return self._nerve.status(project['project-name'], **config)

    def clone(self, name, **config):
        r'''
        Clones a nerve project to local project-root directory

        Ensures given branch is present in the repository

        Args:
            name (str): name of project. Default: None
            \**config: optional config parameters, overwrites fields in a copy of self.config
            verbosity (int, \**config): level of verbosity for output. Default: 0
                Options: 0, 1, 2
            user_branch (str, \**config): branch to clone from. Default: user's branch

        Returns:
            bool: success status
        '''
        return self._nerve.clone(name, **config)

    def request(self, **config):
        r'''
        Request deliverables from the dev branch of given project

        Args:
            \**config: optional config parameters, overwrites fields in a copy of self.config
            user_branch (str, \**config): branch to pull deliverables into. Default: user's branch
            request_include_patterns (list, \**config): list of regular expressions user to include specific deliverables
            request_exclude_patterns (list, \**config): list of regular expressions user to exclude specific deliverables
            verbosity (int, \**config): level of verbosity for output. Default: 0
                Options: 0, 1, 2

        Returns:
            bool: success status
        '''
        project = self._get_project()
        if not project:
            return project
        return self._nerve.request(project['project-name'], **config)

    def publish(self, notes=None, **config):
        r'''
        Attempt to publish deliverables from user's branch to given project's dev branch on Github

        All assets will be published to the user's branch.
        If all deliverables are valid then all data and metadata will be commited
        to the user's branch and merged into the dev branch.
        If not only invalid metadata will be commited to the user's branch

        Args:
            notes (str, optional): notes to appended to project metadata. Default: None
            \**config: optional config parameters, overwrites fields in a copy of self.config
            user_branch (str, \**config): branch to pull deliverables from. Default: user's branch
            publish_include_patterns (list, \**config): list of regular expressions user to include specific assets
            publish_exclude_patterns (list, \**config): list of regular expressions user to exclude specific assets
            verbosity (int, \**config): level of verbosity for output. Default: 0
                Options: 0, 1, 2

        Returns:
            bool: success status
        '''
        project = self._get_project()
        if not project:
            return project
        return self._nerve.publish(project['project-name'], notes=notes, **config)

    def delete(self):
        r'''
        Deletes a nerve project from local storage

        Args:
            None

        Returns:
            bool: success status
        '''
        project = self._get_project()
        if not project:
            return project
        return self._nerve.delete(project['project-name'], False, True)
# ------------------------------------------------------------------------------

class NerveAdmin(NerveUser):
    '''
    Class for interacting with nerve as an administrator

    Args:
        None

    Returns:
        Client: NerveAdmin
    '''
    def __init__(self):
        super().__init__()

    def create(self, name, notes=None, **config):
        r'''
        Creates a nerve project on Github and in the project-root folder

        Created items include:
            Github repository
            dev branch
            nerve project structure
            .lfsconfig
            .gitattributes
            .gitignore

        Args:
            name (str, optional): name of project. Default: None
            notes (str, optional): notes to appended to project metadata. Default: None
            \**config: optional config parameters, overwrites fields in a copy of self.config
            verbosity (int, \**config): level of verbosity for output. Default: 0
                Options: 0, 1, 2

        Returns:
            bool: success status
        '''
        return self._nerve.create(name, notes, **config)

    def delete(self, name, from_server, from_local):
        r'''
        Deletes a nerve project

        Args:
            name (str): name of project
            from_server (bool): delete Github project
            from_local (bool): delete local project directory

        Returns:
            bool: success status
        '''
        return self._nerve.delete(name, from_server, from_local)
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
