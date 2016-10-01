#! /usr/bin/env python
import os
import re
from itertools import *
from git import Repo, GitCommandError
from nerve.core.utils import status
# ------------------------------------------------------------------------------

class Git(object):
    def __init__(self, working_dir, url=None, branch=None):
        self._repo = self._clone(working_dir, url=url, branch=branch)
        self._working_dir = working_dir

    def _clone(self, working_dir, branch=None, url=None):
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

    def create_gitignore(self, patterns=[]):
        path = os.path.join(self._working_dir, '.gitignore')
        with open(path, 'w') as f:
            f.write('\n'.join(patterns))
        return os.path.exists(path)

    def add(self, items=[], all=False):
        if all:
            self._repo.git.add('--all')
        else:
            self._repo.git.add(items)

    def branch(self, name):
        for branch in self._repo.branches:
            if name == branch.name:
                break
        else:
            branch = self._repo.create_head(name)
        branch.checkout()

    def checkout(self, name):
        branch = list(filter(lambda x: x.name == name, self._repo.branches))[0]
        branch.checkout()

    def push(self, branch, origin='origin'):
        self._repo.remote(origin).push(branch)

    def pull(self, origin='origin'):
        self._repo.remote(origin).pull()

    def commit(self, message):
        self._repo.index.commit(message)

    def reset(self, exclude=[]):
        if len(exclude) > 0:
            self._repo.index.reset('HEAD', paths=exclude)
        else:
            self._repo.index.reset('HEAD')

    def status(self, path_re=None, states=[], staged=None, warnings=False):
        return status(
            'git status --porcelain',
            path_re=path_re,
            states=states,
            staged=staged
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
