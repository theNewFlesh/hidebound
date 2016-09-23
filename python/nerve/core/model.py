#! /usr/bin/env python
import os
import yaml
from copy import deepcopy
from itertools import *
from github3 import login
from git import Repo
from configparser import ConfigParser
from nerve.core.utils import execute_subprocess
from nerve.core.git_lfs import GitLFS
# ------------------------------------------------------------------------------

class Nerve(object):
    def __init__(self, config_path):
        # TODO: add validation to config
        config = {}
        with open(config_path, 'r') as f:
            config = yaml.load(f)
        self._client = login(config['username'], token=config['token'])
        self._config = config

    def create(self, name):
        '''
        create nerve project
        '''
        assets = self._config['assets']
        deliverables = self._config['deliverables']
        project_dir = self._config['project_dir']
        extensions = self._config['extensions']
        gitignore = self._config['gitignore']
        spec = self._config['specification']

        repo = self._client.create_repository(name, private=True)
        working_dir = os.path.join(project_dir, name)
        local = Repo.clone_from(repo.ssh_url, working_dir)

        lfs = GitLFS(working_dir)
        lfs.install(skip_smudge=True)

        # create .lfsconfig
        lfsconfig = ConfigParser()
        lfsconfig.add_section('lfs')
        lfsconfig.set('lfs', 'url', 'http://localhost:8080')
        lfsconfig.set('lfs', 'access', 'basic')
        path = os.path.join(working_dir, '.lfsconfig')
        with open(path, 'w') as f:
            lfsconfig.write(f)

        # configure .lfsconfig
        lfs.track(['*.' + x for x in extensions])

        # create .gitignore
        path = os.path.join(working_dir, '.gitignore')
        with open(path, 'w') as f:
            f.write('\n'.join(gitignore))

        # create project subdirectories
        for subdir in chain(assets, deliverables):
            path = os.path.join(working_dir, subdir)
            os.mkdir(path)
            # git won't commit empty directories
            open(os.path.join(path, '.keep'), 'w').close()

        # create project metadata
        config = deepcopy(self._config)
        config['project-name'] = name
        config['project-id'] = repo.id
        config['uri'] = repo.ssh_url
        config['version'] = 1
        # config['uuid'] = None
        with open(os.path.join(working_dir, name + '_meta.yml'), 'w') as f:
            f.write(yaml.dump(config))

        # commit everything
        local.git.add('--all')
        local.index.commit(
            'VALID: {} created according to {} specification'.format(name, spec)
        )

        # create dev branch
        local.create_head('dev')

        # push master
        local.remote().push()
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
