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
import yaml
from nerve.core.project_manager import ProjectManager
from nerve.core.metadata import Metadata
# ------------------------------------------------------------------------------

NERVE_GLOBAL_CONFIG = '/etc/nerve/nerve-global-config.yml'

class NerveUser(object):
    '''
    Class for interacting with nerve as a user

    Args:
        None

    Returns:
        Client: NerveUser
    '''
    def __init__(self):
        config = None
        with open(NERVE_GLOBAL_CONFIG, 'r') as f:
            config = yaml.load(f)
        self._project_manager = ProjectManager(config['nerverc-location'])

    def __getitem__(self, key):
        return self._project_manager.__getitem__(key)

    def __repr__(self):
        return self._project_manager.__repr__()

    def _get_project(self, dirpath):
        '''
        Finds and returns project metadata

        Args:
            None

        Returns:
            dict: Metadata
        '''
        files = os.listdir(dirpath)
        if '.git' in files:
            meta = list(filter(lambda x: re.search('_meta.yml', x), files))
            if len(meta) > 0:
                meta = meta[0]
                meta = os.path.join(dirpath, meta)
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

        \**ConfigParameters:
            * status_include_patterns (list): list of regular expressions user to include specific assets
            * status_exclude_patterns (list): list of regular expressions user to exclude specific assets
            * status_states (list): list of object states files are allowed to be in.
              Options: added, copied, deleted, modified, renamed, updated and untracked
            * log_level (str): logging level. Default: warn

        Yields:
            Metadata: Metadata object of each asset
        '''
        project = self._get_project()
        if not project:
            return project
        return self._project_manager.status(project['project-name'], **config)

    def clone(self, name, **config):
        r'''
        Clones a nerve project to local project-root directory

        Ensures given branch is present in the repository

        Args:
            name (str): name of project. Default: None
            \**config: optional config parameters, overwrites fields in a copy of self.config

        \**ConfigParameters:
            * log_level (str): logging level. Default: warn
            * user_branch (str): branch to clone from. Default: user's branch

        Returns:
            bool: success status
        '''
        return self._project_manager.clone(name, **config)

    def request(self, **config):
        r'''
        Request deliverables from the dev branch of given project

        Args:
            \**config: optional config parameters, overwrites fields in a copy of self.config

        \**ConfigParameters:
            * user_branch (str): branch to pull deliverables into. Default: user's branch
            * request_include_patterns (list): list of regular expressions user to include specific deliverables
            * request_exclude_patterns (list): list of regular expressions user to exclude specific deliverables
            * log_level (str): logging level. Default: warn

        Returns:
            bool: success status
        '''
        project = self._get_project()
        if not project:
            return project
        return self._project_manager.request(project['project-name'], **config)

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

        \**ConfigParameters:
            * user_branch (str): branch to pull deliverables from. Default: user's branch
            * publish_include_patterns (list): list of regular expressions user to include specific assets
            * publish_exclude_patterns (list): list of regular expressions user to exclude specific assets
            * log_level (str): logging level. Default: warn

        Returns:
            bool: success status
        '''
        project = self._get_project()
        if not project:
            return project
        return self._project_manager.publish(project['project-name'], notes=notes, **config)

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
        return self._project_manager.delete(project['project-name'], False, True)
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

    def create(self, name, notes=None, **project):
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
            \**project: optional project parameters, overwrites fields in a copy of self.project_template

        Returns:
            bool: success status
        '''
        return self._project_manager.create(name, notes, {}, **project)

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
        return self._project_manager.delete(name, from_server, from_local)
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
