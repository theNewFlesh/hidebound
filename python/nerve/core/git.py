#! /usr/bin/env python
import os
import re
from itertools import *
from git import Repo
# ------------------------------------------------------------------------------

class Git(object):
    def __init__(self, working_dir=None):
        if working_dir:
            self._repo = Repo(working_dir)
            os.chdir(working_dir)

    def create_gitignore(self, patterns=[]):
        path = os.path.join(self._working_dir, '.gitignore')
        with open(path, 'w') as f:
            f.write('\n'.join(patterns))
        return os.path.exists(path)

    def clone(self, url, working_dir):
        self._repo = Repo.clone_from(url, working_dir)
        return os.path.exists(working_dir)

    def add(self, items=[], all=False):
        if all:
            self._repo.add('--all')
        else:
            self._repo.add(items)

    def branch(self, name):
        self._repo.create_head(name)
        branch = list(filter(lambda x: x.name == name, self._repo.branches))[0]
        branch.checkout()

    def push(self, branch, origin='master'):
        self._repo.origin(origin).push(branch)

    def pull(self, origin='master'):
        self._repo.remote(origin).pull()

    def commit(self, message):
        self._repo.index.commit(message)

    def reset(self, exclude=[]):
        if len(exclude) > 0:
            self._repo.index.reset('HEAD', paths=exclude)
        else:
            self._repo.index.reset('HEAD')

    def status(self, path_re=None, states=[], staged=None):
        if path_re:
            path_re = re.compile(path_re)

        for item in self._repo.index.diff('HEAD', R=True):
            lut = dict(
                A='added',
                C='copied',
                D='deleted',
                M='modified',
                R='renamed',
                U='updated'
            )
            output = dict(
                filepath=item.a_path, # is this always correct?
                state=lut[item.change_type],
                staged=True
            )

            if path_re:
                found = path_re.search(output['filepath'])
                if not found:
                    continue
            if states:
                if output['state'] not in states:
                    continue
            if staged:
                if output['staged'] != staged:
                    continue

            yield output
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
