#! /usr/bin/env python
import os
import yaml
from copy import deepcopy
from itertools import *
from github3 import login
from github3.repos.branch import Branch
from github3.null import NullObject
# ------------------------------------------------------------------------------

class Client(object):
    def __init__(self, config):
        if isinstance(config, str):
            with open(config, 'r') as f:
                config = yaml.load(f)

        client = login(config['username'], token=config['token'])
        org = client.organization(config['organization'])

        repo = client.repository(config['organization'], config['name'])
        if isinstance(repo, NullObject):
            repo = org.create_repository(
                config['organization'],
                config['name'],
                private=config['private']
            )

        if config['uri-type'] is 'ssh':
            config['uri'] = repo.ssh_url
        elif config['uri-type'] is 'http':
            config['uri'] = repo.http_url

        config['id'] = repo.id

        self._config = config
        self._client = client
        self._org = org
        self._repo = repo

    def __getitem__(self, key):
        return self._config[key]

    @property
    def config(self):
        return deepcopy(self._config)

    def has_branch(self, name, wait=False):
        response = isinstance(self._repo.branch(name), Branch)
        if wait:
            while reponse is False:
                response = isinstance(self._repo.branch(name), Branch)
        return response

    def set_default_branch(self, name):
        self._repo.edit(self['name'], default_branch=name)
        return True
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

__all__ = ['Client']

if __name__ == '__main__':
    main()
