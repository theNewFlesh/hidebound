#! /usr/bin/env python
import os
import yaml
import json
from copy import deepcopy
from itertools import *
from github3 import login
from github3.repos.branch import Branch
from github3.null import NullObject
# ------------------------------------------------------------------------------

# TODO: added waiting and timeout logic
# TODO: handle github errors

class Client(object):
    def __init__(self, config):
        if isinstance(config, str):
            with open(config, 'r') as f:
                config = yaml.load(f)

        self._client = login(config['username'], token=config['token'])
        self._org = self._client.organization(config['organization'])
        self._team_ids = {team.name: team.id for team in self._org.teams()}
        self._repo = self._create_repository(
            config['name'],
            config['organization'],
            config['private']
        )

        if config['url-type'] == 'ssh':
            config['url'] = self._repo.ssh_url
        elif config['url-type'] == 'http':
            config['url'] = self._repo.http_url
        config['fullname'] = self._repo.full_name
        config['id'] = self._repo.id

        self._config = config

    def __getitem__(self, key):
        return self._config[key]

    def _create_repository(self, name, orgname, private):
        repo = self._client.repository(orgname, name)
        if isinstance(repo, NullObject):
            repo = self._org.create_repository(
                name,
                private=private
            )
        return repo
    # --------------------------------------------------------------------------

    @property
    def config(self):
        return deepcopy(self._config)

    # def create_branch(self, name):
    #     if self.has_branch(name, wait=True):
    #         return True
        # github3 has no ability to create a branch

    def has_branch(self, name, wait=False):
        response = isinstance(self._repo.branch(name), Branch)
        if wait:
            while response is False:
                response = isinstance(self._repo.branch(name), Branch)
        return response

    def set_default_branch(self, name):
        self._repo.edit(self['name'], default_branch=name)
        return True

    def add_team(self, name, permission):
        # add_repository is fixed in develop branch of gihub3
        # making this code obsolete
        lut = dict(
            read='pull',
            write='push',
            pull='pull',
            push='push'
        )
        perm = lut[permission]
        perm = {'permission': perm}

        id_ = self._team_ids[name]
        team = self._org.team(id_)
        url = team._build_url('repos', self['fullname'], base_url=team._api)
        return team._boolean(team._put(url, data=json.dumps(perm)), 204, 404)

    def create_pull_request(self, title, base, head, body=None):
        request = self._repo.create_pull(title, base, head, body=body)
        return request.number

    def merge_pull_request(self, number, message=''):
        return self._repo.pull_request(number).merge(message)

    def delete(self):
        self._repo.delete()
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
