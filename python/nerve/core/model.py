#! /usr/bin/env python
import os
import yaml
from copy import deepcopy
from itertools import *
from github3 import login
from git import Repo
from github3.repos.branch import Branch
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
        root = self._config['project-root']
        extensions = self._config['extensions']
        gitignore = self._config['gitignore']
        spec = self._config['specification']
        orgname = self._config['organization']
        # ----------------------------------------------------------------------

        # create repo on github
        org = self._client.organization(orgname)
        repo = org.create_repository(name, private=True)
        project = os.path.join(root, name)
        local = Repo.clone_from(repo.ssh_url, project)
        # ----------------------------------------------------------------------

        lfs = GitLFS(project)
        lfs.install(skip_smudge=True)

        # create .lfsconfig
        lfsconfig = ConfigParser()
        lfsconfig.add_section('lfs')
        lfsconfig.set('lfs', 'url', 'http://localhost:8080')
        lfsconfig.set('lfs', 'access', 'basic')
        path = os.path.join(project, '.lfsconfig')
        with open(path, 'w') as f:
            lfsconfig.write(f)

        # configure .lfsconfig
        lfs.track(['*.' + x for x in extensions])
        # ----------------------------------------------------------------------

        # create .gitignore
        path = os.path.join(project, '.gitignore')
        with open(path, 'w') as f:
            f.write('\n'.join(gitignore))
        # ----------------------------------------------------------------------

        # create project subdirectories
        for subdir in chain(assets, deliverables):
            path = os.path.join(project, subdir)
            os.mkdir(path)
            # git won't commit empty directories
            open(os.path.join(path, '.keep'), 'w').close()

        # create project metadata
        config = deepcopy(self._config)
        del config['token']
        config['project-name'] = name
        config['project-id'] = repo.id
        config['uri'] = repo.ssh_url
        config['version'] = 1
        # config['uuid'] = None
        with open(os.path.join(project, name + '_meta.yml'), 'w') as f:
            f.write(yaml.dump(config))
        # ----------------------------------------------------------------------

        # commit everything
        local.git.add('--all')
        local.index.commit(
            'VALID: {} created according to {} specification'.format(name, spec)
        )

        # push master
        local.remote().push()

        # create dev branch
        local.create_head('dev')
        dev = list(filter(lambda x: x.name == 'dev', local.branches))[0]
        dev.checkout()
        local.remote().push('dev')

        # wait for response
        response = None
        while not isinstance(response, Branch):
            response = repo.branch('dev')

        # set default branch to dev
        repo.edit(name, default_branch='dev')

        # TODO: send data to DynamoDB

    def clone(self, name):
        '''
        clone nerve project
        '''
        # TODO catch repo already exists errors and repo doesn't exist errors

        org = self._config['organization']
        token = self._config['token']
        root = self._config['project-root']
        project = os.path.join(root, name)
        repo = self._client.repository(org, name)
        local = Repo.clone_from(repo.ssh_url, project)

        # create user-branch
        ubranch = self._config['user-branch']
        local.create_head(ubranch)
        ubranch = list(filter(lambda x: x.name == ubranch, local.branches))[0]
        ubranch.checkout()

    def request(self, project=os.getcwd(), include=[], exclude=[]):
        '''
        request nerve assets
        '''
        # TODO ensure pulls only come from dev branch
        if include == []:
            include = self._config['include-assets-for-request']
        if exclude == []:
            exclude = self._config['exclude-assets-for-request']

        Repo(project).remote().pull()
        GitLFS(project).pull(include, exclude)

    def publish(self, project=os.getcwd(), include=[]):
        '''
        publish nerve assets
        '''
        # TODO: add branch support
        if include == []:
            include = self._config['include-assets-for-publishing']

        repo = Repo(project)
        # pulling metadata first avoids merge conflicts
        # by setting HEAD to the most current
        repo.remote().pull()

        repo.index.add(include)
        repo.index.diff('HEAD', R=True).iter_change_type('A') # new files only
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
