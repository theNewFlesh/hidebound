#! /usr/bin/env python
'''
The model module contains the Git class, nerve's internal API for accessing git

Platforrm:
    Unix

Author:
    Alex Braun <alexander.g.braun@gmail.com> <http://www.alexgbraun.com>
'''
# ------------------------------------------------------------------------------

import os
import re
import git
from git import Repo
from git import GitCommandError
from nerve.core.utils import get_status
# ------------------------------------------------------------------------------

class Git(git.Git):
    '''
    Class for interacting with a single local git repository

    API: create_gitignore, add, branch, checkout, push, pull, commit, reset, status

    Args:
        working_dir (str): fullpath of git repository
        url (str, optional): url to clone Github repository from. Default: None
        branch (str, optional): branch to clone from or checkout. Default: None

    Returns:
        Git: local git repository
    '''
    def __init__(self, working_dir, url=None, branch=None, environment={}):
        super().__init__()
        self.update_environment(**environment)
        self._env = environment
        self._repo = self._clone(working_dir, url=url, branch=branch)
        self._working_dir = working_dir
        os.chdir(working_dir)

    def _clone(self, working_dir, url=None, branch=None):
        '''
        Convenience method for cloning a GitHub repository

        Args:
            working_dir (str): fullpath of git repository location
            url (str, optional): url to clone Github repository from. Default: None
            branch (str, optional): branch to clone from or checkout. Default: None

        Returns:
            git.Repo: local repository

        .. todo::
            - fix try block so that it raises an error when ssh-agent isn't
              running or ssh private has not been added
        '''
        os.chdir(os.path.split(working_dir)[0])
        if url:
            # try:
            if branch:
                return Repo.clone_from(to_path=working_dir, url=url, branch=branch)
            else:
                return Repo.clone_from(to_path=working_dir, url=url)
            # except GitCommandError as e:
            #     # directory already exists
            #     if e.status != 128:
            #         raise GitCommandError(e)

        repo = Repo(working_dir)
        if branch:
            if repo.active_branch.name != branch:
                branch = list(filter(lambda x: x.name == branch, repo.branches))[0]
                branch.checkout()

        return repo

    def _get_branch(self, name):
        for branch in self._repo.branches:
            if branch.name == name:
                return branch
        return None

    def _delete_index_on_error(self, func, *args, **kwargs):
        try:
            func(*args, **kwargs)
        except GitCommandError as e:
            # if 'File exists' not in e.stderr.decode():
            if re.search('.git/index.lock|new index file', e.stderr.decode()):
                os.remove(os.path.join(self._working_dir, '.git', 'index'))
                self.reset()
                func(*args, **kwargs)
            else:
                raise GitCommandError(e)
    # --------------------------------------------------------------------------

    def create_gitignore(self, patterns):
        '''
        Create a .gitignore file in the root path of the local git repository

        Args:
            patterns (list): gitignore patterns (glob style)

        Returns:
            bool: existence of .gitignore file
        '''
        path = os.path.join(self._working_dir, '.gitignore')
        with open(path, 'w') as f:
            f.write('\n'.join(patterns))
        return os.path.exists(path)

    def add(self, items=[], all=False):
        '''
        Stage items for git commit

        Args:
            items (list, optional): filepaths to be added
            all (bool, optional): commit all items

        Returns:
            None
        '''
        if all:
            self._repo.git.add('--all')
        else:
            self._repo.git.add(items)

    def branch(self, name):
        '''
        Checkout a given branch, create it if necessary

        Args:
            name (str): branch name

        Returns:
            None
        '''
        for branch in self._repo.branches:
            if name == branch.name:
                break
        else:
            branch = self._repo.create_head(name)
        branch.checkout()

    def push(self, branch, remote='origin'):
        '''
        Push comit to given branch

        Args:
            branch (str): branch name
            remote (str, optional): remote repository. Default: origin

        Returns:
            None
        '''
        self._repo.remote(remote).push(branch)

    def pull(self, branch, remote='origin'):
        '''
        Pull upstream commits from remote branch

        Args:
            remote (str, optional): remote repository. Default: origin

        Returns:
            None
        '''
        branch = self.references([branch], reftypes=['remote'])
        branch = list(branch)[0]
        branch = branch['branch']
        self._repo.remote(remote).pull(branch)

    def merge(self, src, dest):
        '''
        Merge source branch into destination branch

        Arguments:
            src (str): source branch
            dest (str): destination branch

        Returns:
            None
        '''
        src = self._get_branch(src)
        dest = self._get_branch(src)
        self._repo.merge_base(src, dest)

    def commit(self, message):
        '''
        Commit staged files

        Args:
            message (str): commit message

        Returns:
            None
        '''
        self._repo.index.commit(message)

    def reset(self, exclude=[]):
        '''
        Remove files staged for commit excluding given fullpaths

        Args:
            exclude (list, optional): fullpaths of files to be reatined in commit

        Returns:
            None
        '''
        if len(exclude) > 0:
            self._repo.index.reset('HEAD', paths=exclude)
        else:
            self._repo.index.reset('HEAD')

    def references(self, branches=[], reftypes=['local', 'remote']):
        '''
        Yields reference object information

        Args:
            branches (list, optional): limit references to these branches. Default: all branches
            reftypes (list, optional): limit references to local and/or remote repositories. Default: both

        Yields:
            dict: reference
        '''
        for ref in self._repo.references:
            output = dict(
                name=ref.name,
                fullpath=ref.abspath,
                path=ref.path,
                branch=os.path.split(ref.name)[-1],
                commit=ref.object.hexsha,
                remote=ref.is_remote()
            )
            if output['branch'] == 'HEAD':
                output['branch'] = ref.repo.active_branch.name
            # ------------------------------------------------------------------

            flag = True
            if len(branches) > 0:
                if output['branch'] not in branches:
                    flag = False
            if 'local' not in reftypes:
                if not output['remote']:
                    flag = False
            if 'remote' not in reftypes:
                if output['remote']:
                    flag = False

            if flag:
                yield output

    def status(self, include=[], exclude=[], states=[], staged=None, warnings=False):
        '''
        Get the status of the repositories files

        Args:
            include (list, optional): list of regex patterns used to include files. Default: []
            exclude (list, optional): list of regex patterns used to exclude files. Default: []
            states (list, optional): file states to be shown in output. Default: all states
                Options: added, copied, deleted, modified, renamed, updated, untracked
            staged (bool, optional): include only files which are staged or unstaged. Default: both
            warnings (bool, optional): display warnings

        Returns:
            list: list of dicts, each one representing a file
        '''
        return get_status(
            'git status --porcelain',
            self._working_dir,
            include=include,
            exclude=exclude,
            states=states,
            staged=staged,
            warnings=warnings
        )

    @property
    def url(self):
        '''
        str: repo url
        '''
        return list(self._repo.remote('origin').urls)[0]
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

__all__ = ['Git']

if __name__ == '__main__':
    main()
