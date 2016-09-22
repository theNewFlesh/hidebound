#! /usr/bin/env python
import os
import yaml
from github3 import login
from git import Repo
from configparser import ConfigParser
from nerve.core.utils import execute_subprocess
from nerve.core.git_lfs import GitLFS
# ------------------------------------------------------------------------------

class Nerve(object):
    def __init__(self, config_path):
        config = {}
        with open(config_path, 'r') as f:
            config = yaml.load(f)
        self._client = login(config['username'], token=config['token'])
        self._config = config

    def create(self, name):
        repo = self._client.create_repository(name)
        working_dir = os.path.join(self._project_dir, name)
        local = Repo.clone_from(repo.clone_url, working_dir)
        repo.edit(name, private=True) # must be made private after clone

        lfs = GitLFS(working_dir)
        lfs.install(skip_smudge=True)

        config = ConfigParser()
        config.add_section('lfs')
        config.add('lfs', 'url', 'http://localhost:8080')
        config.add('lfs', 'access', 'basic')
        path = os.path.join(working_dir, '.lfsconfig')
        with open(path, 'w') as f:
            config.write(f)

        lfs.track(['*.' + x for x in extensions])
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

__all__ = ['Nerve']

if __name__ == '__main__':
    main()
