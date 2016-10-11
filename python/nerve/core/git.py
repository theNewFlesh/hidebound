#! /usr/bin/env python
import os
from git import Repo, GitCommandError
from nerve.core import utils
# ------------------------------------------------------------------------------

'''
The model module contains the Git class, nerve's internal API for accessing git

Platforrm:
    Unix

Author:
    Alex Braun <alexander.g.braun@gmail.com> <http://www.alexgbraun.com>
'''

class Git(object):
    '''
    Class for interacting with a single local git repository

    API: create_gitignore, add, branch, checkout, push, pull, commit, reset, status
    '''
    def __init__(self, working_dir, url=None, branch=None):
        '''
        Client constructor creates and acts as a single local git repository

        Args:
            working_dir (str): fullpath of git repository
            url (str, optional): url to clone Github repository from. Default: None
            branch (str, optional): branch to clone from or checkout. Default: None

        Returns:
            Git: local git repository
        '''
        self._repo = self._clone(working_dir, url=url, branch=branch)
        self._working_dir = working_dir

    def _clone(self, working_dir, url=None, branch=None):
        '''
        Convenience method for cloning a GitHub repository

        Args:
            working_dir (str): fullpath of git repository location
            url (str, optional): url to clone Github repository from. Default: None
            branch (str, optional): branch to clone from or checkout. Default: None

        Returns:
            git.Repo: local repository
        '''
        os.chdir(os.path.split(working_dir)[0])
        if url:
            try:
                if branch:
                    return Repo.clone_from(to_path=working_dir, url=url, branch=branch)
                else:
                    return Repo.clone_from(to_path=working_dir, url=url)
            except GitCommandError as e:
                # directory already exists
                if e.status != 128:
                    raise GitCommandError(e)

        repo = Repo(working_dir)
        if branch:
            branch = list(filter(lambda x: x.name == branch, repo.branches))[0]
            branch.checkout()

        return repo
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

    def pull(self, src, dest, remote='origin'):
        '''
        Pull upstream commits from remote branch

        Args:
            remote (str, optional): remote repository. Default: origin

        Returns:
            None
        '''
        src = self.references([src], reftypes=['remote'])
        src = list(src)[0]
        src = src['branch']

        dest = self.references([dest], reftypes=['local'])
        dest = list(dest)[0]
        dest = dest['branch']

        self._repo.remote(remote).pull(src + ':' + dest)

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
                options include: added, copied, deleted, modified, renamed, updated, untracked
            staged (bool, optional): include only files which are staged or unstaged. Default: both
            warnings (bool, optional): display warnings

        Returns:
            list: list of dicts, each one representing a file
        '''
        return utils.status(
            'git status --porcelain',
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

__all__ = ['Git']

if __name__ == '__main__':
    main()
