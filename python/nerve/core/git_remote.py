#! /usr/bin/env python
'''
The model module contains the Client class, nerve's internal API for accessing Github

Platforrm:
    Unix

Author:
    Alex Braun <alexander.g.braun@gmail.com> <http://www.alexgbraun.com>

.. todo::
    - added waiting and timeout logic
    - handle github errors
'''
# ------------------------------------------------------------------------------

from copy import deepcopy
import json
import signal
from time import sleep
from github3 import login
from github3.repos.branch import Branch
from github3.null import NullObject
from nerve.core.metadata import Metadata
from nerve.core.errors import TimeoutError
# ------------------------------------------------------------------------------

class GitRemote(object):
    '''
    Class for interacting with a single repository on Github

    Attributes:
        config (dict): a dictionary representing Nerve's internal configuration

    API:
        has_branch
        set_default_branch
        add_team
        delete
        create_pull_request
        merge_pull_request

    Args:
        config (dict): a nerve project configuration (derived from nerverc)

    Returns:
        Client: Github repository
    '''
    def __init__(self, config):
        config = Metadata(config)
        config.validate()
        config = config.data

        self._client = login(config['username'], token=config['token'])
        self._org = self._client.organization(config['organization'])
        self._team_ids = {team.name: team.id for team in self._org.teams()}
        self._repo = self._get_repository(
            config['project-name'],
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

    def _get_repository(self, name, orgname, private):
        '''
        Gets a repository on GitHub. Creates one if it doesn't exist.

        Args:
            name (str): repository name
            organme (str): GitHub organization name
            private (bool): repository availability

        Returns:
            github3.repos.repo.Repository
        '''
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
        '''
        dict: a copy of this object's configuration
        '''
        return deepcopy(self._config)

    def has_branch(self, name, timeout=0):
        '''
        Checks whether Github repository has a given branch

        Args:
            name (str): branch name

        Returns:
            bool: branch status
        '''
        def _handler(signum, frame):
            raise TimeoutError()

        result = isinstance(self._repo.branch(name), Branch)

        if timeout > 0:
            signal.signal(signal.SIGALRM, _handler)
            signal.alarm(timeout)
            try:
                while not result:
                    sleep(0.25)
                    result = isinstance(self._repo.branch(name), Branch)
                return result
            except:
                pass
        return result

    def set_default_branch(self, name):
        '''
        Sets default branch of GitHub repository

        Args:
            name (str): branch name

        Returns:
            bool: success status
        '''
        self._repo.edit(self['project-name'], default_branch=name)
        return True

    def add_team(self, name, permission):
        '''
        Checks whether Github repository has a given branch

        Args:
            name (str): branch name
            permission (str): team permissions. Values include: read, write, pull, push

        Returns:
            bool: success status
        '''
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

    def create_pull_request(self, title, base, branch, body=None):
        '''
        Creates a pull request to merge a head commit of branch into a base branch on Github

        Args:
            title (str): title of pull request
            base (str): branch to merge head into
            branch (str): branch to be merged
            body (str): markdown formatted string to put in the comments

        Returns:
            int: pull request number
        '''
        request = self._repo.create_pull(title, base, branch, body=body)
        return request.number

    def merge_pull_request(self, number, message=''):
        '''
        Merges a given pull request on GitHub

        Args:
            number (int): pull request number
            message (str, optional): commit message. Default: ''

        Returns:
            bool: success status
        '''
        return self._repo.pull_request(number).merge(message)

    def delete(self):
        '''
        Deletes repository off of Github

        Args:
            None

        Returns:
            bool: success status
        '''
        self._repo.delete()
        return True

    def get_head_sha(self, branch='master'):
        return self._repo.branch(branch).commit.sha
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

__all__ = ['GitRemote']

if __name__ == '__main__':
    main()
