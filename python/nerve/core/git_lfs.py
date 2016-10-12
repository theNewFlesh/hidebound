#! /usr/bin/env python
'''
The model module contains the GitFS class, nerve's internal API for accessing git lfs

Platforrm:
    Unix

Author:
    Alex Braun <alexander.g.braun@gmail.com> <http://www.alexgbraun.com>

.. todo::
    - integrate python-based git-lfs server instead of using git-lfs-s3 which is ruby-based
'''
# ------------------------------------------------------------------------------

import os
from configparser import ConfigParser
from nerve.core import utils
from nerve.core.utils import execute_subprocess
# ------------------------------------------------------------------------------

class GitLFS(object):
    '''
    Class for sending and parsing git lfs commands executed upon a single local git repository

    API: working_dir, create_config, install, track, pull, status
    '''
    def __init__(self, working_dir):
        '''
        Client constructor creates and acts as a single local git lfs repository

        Changes current working directory of process to woking_dir.
        Starts local lfs server.

        Args:
            working_dir (str): fullpath of git repository (must exist)

        Returns:
            GitLFS: local git lfs repository
        '''
        self._working_dir = working_dir
        os.chdir(working_dir)
        # start server
        # execute_subprocess('git-lfs-s3')

    @property
    def working_dir(self):
        '''
        str: fullpath of local git repository
        '''
        return self._working_dir

    def create_config(self, url, access='basic'):
        '''
        Creates a .lfsconfig file in the root path of the local git repository

        Args:
            url (str): url of local git lfs server (eg. http://localhost:8080)
            access (str, optional): git lfs access rights. Default: 'basic'

        Returns:
            bool: existence of .lfsconfig file
        '''
        lfsconfig = ConfigParser()
        lfsconfig.add_section('lfs')
        lfsconfig.set('lfs', 'url', url)
        lfsconfig.set('lfs', 'access', access)
        path = os.path.join(self._working_dir, '.lfsconfig')
        with open(path, 'w') as f:
            lfsconfig.write(f)

        return os.path.exists(path)

    def install(self, force=False, local=False, skip_smudge=False):
        '''
        Perform the following actions to ensure that Git LFS is setup properly:

        * Set up the clean and smudge filters under the name "lfs" in the global Git
          config.
        * Install a pre-push hook to run git lfs pre-push for the current repository,
          if run from inside one. If "core.hooksPath" is configured in any Git
          configuration (and supported, i.e., the installed Git version is at least
          2.9.0), then the pre-push hook will be installed to that directory instead.

        Without any options, git lfs install will only setup the "lfs" smudge and clean
        filters if they are not already set.

        Args:
            force (bool, optional): sets the "lfs" smudge and clean filters, overwriting existing values
            local (bool, optional): sets the "lfs" smudge and clean filters in the local repository's git
                config, instead of the global git config (~/.gitconfig)
            skip-smudge (bool, optional): skips automatic downloading of objects
                on clone or pull. This requires a manual "git lfs pull" every
                time a new commit is checked out on your repository

        Returns:
            List: list of strings detailing stdout of command
        '''
        cmd = 'git lfs install'
        # --system ommitted
        if force:
            cmd += ' --force'
        if local:
            cmd += ' --local'
        if skip_smudge:
            cmd += ' --skip-smudge'

        return execute_subprocess(cmd)

    def track(self, extensions=[]):
        '''
        Track files with certain file extensions through git lfs

        Args:
            extensions (list or str): list of file extensions specifying file extensions to be tracked

        Example:
            lfs.track(['png', 'obj', 'jpg'])

        Returns:
            List: list of strings detailing stdout of command
        '''
        if isinstance(extensions, str):
            extensions = [extensions]
        cmd = 'git lfs track'
        for exp in extensions:
            execute_subprocess(cmd + ' ' + exp)

        output = execute_subprocess(cmd, 'no matches found:.*')
        output = [x.lstrip().split(' ') for x in output[1:-1]]
        return output

    def pull(self, include=[], exclude=[]):
        '''
        Pull data from git lfs, replacing local pointer files with their actual data

        Args:
            include (list, optional): list of glob patterns used to include files. Default: []
            exclude (list, optional): list of glob patterns used to exclude files. Default: []

        Returns:
            List: list of strings detailing stdout of command
        '''
        cmd = 'git lfs pull'
        if len(include) > 0:
            cmd += ' -I ' + ','.join(include)
        if len(exclude) > 0:
            cmd += ' -X ' + ','.join(exclude)

        return execute_subprocess(cmd)

    def status(self, include=[], exclude=[], states=[], staged=None, warnings=False):
        '''
        Get the status of the tracked git lfs files

        Args:
            include (list, optional): list of regex patterns used to include files. Default: []
            exclude (list, optional): list of regex patterns used to exclude files. Default: []
            states (list, optional): file states to be shown in output. Default: all states
                options include: added, copied, deleted, modified, renamed, updated, untracked
            staged (bool, optional): include only files which are staged or unstaged. Default: both
            warnings (bool, optional): display warnings

        Returns:
            list: list of dicts, each one representing a file
        '''
        return utils.status(
            'git lfs status --porcelain',
            include=include,
            exclude=exclude,
            states=states,
            staged=staged,
            warnings=warnings
        )
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

__all__ = ['GitLFS']

if __name__ == '__main__':
    main()
