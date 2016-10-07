#! /usr/bin/env python
import os
import shutil
import yaml
from copy import deepcopy
from itertools import *
from warnings import warn
from nerve.core.git import Git
from nerve.core.git_lfs import GitLFS
from nerve.core.client import Client
from nerve.core.metadata import Metadata
# ------------------------------------------------------------------------------

'''
The model module contains the Nerve class, the central component of the entire
nerve framework.

Platforrm:
    Unix

Author:
    Alex Braun <alexander.g.braun@gmail.com> <http://www.alexgbraun.com>
'''

class Nerve(object):
    '''
    Class for handling nerve projects

    Attributes:
        config (dict): a dictionary representing Nerve's internal configuration

    API:
        create, clone, request, publish and delete
    '''
    def __init__(self, config):
        '''
        Nerve constructor that takes a nerverc configuration (yaml format)

        Args:
            config (str or dict): a fullpath to a nerverc config or a dict of one

        Returns:
            Nerve
        '''
        config = Metadata(config, 'config001')
        config.validate()
        self._config = config

    def __getitem__(self, key):
        return self._config[key]

    def _create_subdirectories(self, project):
        '''
        Creates directory structure for a nerve project

        Args:
            project (str): fullpath to project

        Returns:
            None
        '''
        for subdir in chain(self['assets'], self['deliverables']):
            path = os.path.join(project, subdir)
            os.mkdir(path)
            # git won't commit empty directories
            open(os.path.join(path, '.keep'), 'w').close()

    def _create_metadata(self, project, name, project_id, url, version=1):
        '''
        Creates a [project]_v[###]_meta.yml file in the base of the project

        Args:
            project (str): fullpath to project
            name (str): name of project
            project_id (str): github repository id
            url (str): clone url for repository
            version (int, optional): the version of this projects configuration. Default: 1

        Returns:
            None
        '''
        config = deepcopy(self._config)
        del config['token']
        config['project-name'] = name
        config['project-id'] = project_id
        config['url'] = url
        config['version'] = 1
        # config['uuid'] = None

        # version implicitly
        with open(os.path.join(project, name + '_meta.yml'), 'w') as f:
            yaml.dump(config, f)

    def _get_client(self, name):
        '''
        Convenience method for returning a Client class object

        Args:
            name (str): name of project

        Returns:
            Client: Github repository
        '''
        config = self.config
        config['name'] = name
        return Client(config)

    def _get_project_and_branch(self, name, branch):
        '''
        Convenience method for returning a project path and branch name

        Args:
            name (str): name of project
            branch (str, optional): name of branch. Default: user-branch

        Returns:
            tuple(str, str): project name and branch name
        '''
        project = os.path.join(self['project-root'], name)
        if branch == 'user-branch':
            branch = self['user-branch']
        return project, branch
    # --------------------------------------------------------------------------

    @property
    def config(self):
        '''
        Returns a copy of this object's configuration

        Returns:
            dict: internal configuration
        '''
        return deepcopy(self._config)

    def create(self, name):
        '''
        Creates a nerve project on Github and in the project-root folder

        Created items include:
            Github repository
            dev branch
            nerve project structure
            .lfsconfig
            .gitattributes
            .gitignore

        Args:
            name (str): name of project

        Returns:
            bool: success status
        '''
        # create repo
        project = os.path.join(self['project-root'], name)
        client = self._get_client(name)
        local = Git(project, url=client['url'])
        # ----------------------------------------------------------------------

        # configure repo
        lfs = GitLFS(project)
        lfs.install(skip_smudge=True)
        lfs.create_config('http://localhost:8080')
        lfs.track(['*.' + x for x in self['extensions']])
        local.create_gitignore(self['gitignore'])
        # ----------------------------------------------------------------------

        # ensure first commit is on master branch
        local.add(all=True)
        local.commit('initial commit')
        local.push('master')
        # ----------------------------------------------------------------------

        # create project structure
        local.branch('dev')
        self._create_subdirectories(project)
        self._create_metadata(project, name, client['id'], client['url'])
        # ----------------------------------------------------------------------

        # commit everything
        local.add(all=True)
        local.commit(
            'VALID: {} created according to {} specification'.format(
                name,
                self['specification']
            )
        )
        local.push('dev')
        client.has_branch('dev')
        client.set_default_branch('dev')

        # cleanup
        shutil.rmtree(project)
        # ----------------------------------------------------------------------

        # add teams
        for team, perm in self['teams'].items():
            client.add_team(team, perm)

        # TODO: send data to DynamoDB

        return True

    def clone(self, name, branch='user-branch'):
        '''
        Clones a nerve project to local project-root directory

        Ensures given branch is present in the repository

        Args:
            name (str): name of project
            branch (str, optional): branch to clone from. Default: user's branch

        Returns:
            bool: success status
        '''
        # TODO: catch repo already exists errors and repo doesn't exist errors
        project, branch = self._get_project_and_branch(name, branch)
        client = self._get_client(name)
        if client.has_branch(branch):
            local = Git(project, url=client['url'], branch=branch)
        else:
            local = Git(project, url=client['url'], branch='dev')

            # this done in lieu of doing it through github beforehand
            local.branch(branch)
            local.push(branch)

        return True

    def request(self, name, branch='user-branch', include=[], exclude=[]):
        '''
        Request deliverables from the dev branch of given project

        Args:
            name (str): name of project
            branch (str, optional): branch to pull deliverables into. Default: user's branch
            include (list, optional): list of regular expressions user to include specific deliverables
            exclude (list, optional): list of regular expressions user to exclude specific deliverables

        Returns:
            bool: success status
        '''
        project, branch = self._get_project_and_branch(name, branch)

        # TODO: ensure pulls only come from dev branch
        if len(include) == 0:
            include = self['request-include-patterns']
        if len(exclude) == 0:
            exclude = self['request-exclude-patterns']

        client = self._get_client(name)
        title = '{user} attempts to request deliverables from dev'
        title = title.format(user=self['user-branch'])
        # body = fancy markdown detailing request?
        # num = client.create_pull_request(title, branch, 'dev')
        # additional dev to user-branch logic here if needed
        # if used/implemented propely merge-conflict logic will not be necessary
        # here
        # client.merge_pull_request(num, 'Request authorized')

        Git(project, branch=branch).pull('dev', branch)
        GitLFS(project).pull(include, exclude)

        return True

    def publish(self, name, branch='user-branch', include=[], exclude=[], verbosity=0):
        '''
        Attempt to publish deliverables from user's branch to given project's dev branch on Github

        All assets will be published to the user's branch.
        If all deliverables are valid then all data and metadata will be commited
        to the user's branch and merged into the dev branch.
        If not only invalid metadata will be commited to the user's branch

        Args:
            name (str): name of project
            branch (str, optional): branch to pull deliverables from. Default: user's branch
            include (list, optional): list of regular expressions user to include specific assets
            exclude (list, optional): list of regular expressions user to exclude specific assets
            verbosity (int, optional): level of events to print to stdout. Default: 0

        Returns:
            bool: success status
        '''
        project, branch = self._get_project_and_branch(name, branch)
        wrn = False
        if verbosity > 0:
            wrn = True
        if len(include) == 0:
            include = self['publish-include-patterns']
        if len(exclude) == 0:
            exclude = self['publish-exclude-patterns']
        # ----------------------------------------------------------------------

        # PULL METADATA FROM DEV

        # pulling metadata first avoids merge conflicts
        # by setting HEAD to the most current
        # TODO: add branch checking logic to skip the following if not needed?

        client = self._get_client(name)
        # title = 'Ensuring {branch} is up to date with dev'.format(branch=branch)
        # body = fancy markdown detailing publish?
        # num = client.create_pull_request(title, 'dev', branch)
        # additional user-branch to dev logic here if needed
        # if used/implemented propely merge-conflict logic will not be necessary
        # here
        # client.merge_pull_request(num, 'Update complete')
        local = Git(project)
        local.pull('dev', branch)
        # ----------------------------------------------------------------------

        # GET DATA

        # get only added assets
        lfs = GitLFS(project)
        assets = lfs.status(include=include, exclude=exclude, warnings=wrn)
        # ----------------------------------------------------------------------

        # GENERATE METADATA FILES

        nondeliv = []
        valid = []
        invalid = []
        for asset in assets:
            # meta receives a asset, search for a metadata file
            # if it exists, meta loads that metadata into an internal variable
            # meta then generates metadata from the asset and overwrites
            # its internal metadata with it

            # VALIDATE METADATA
            meta = Metadata(asset['fullpath'])
            if meta.deliverable:
                if asset['state'] is 'added':
                    if meta.valid:
                        valid.append(meta)
                    else:
                        invalid.append(meta)
                    meta.write()
            else:
                nondeliv.append(asset['fullpath'])
        # ----------------------------------------------------------------------

        # PUSH ASSETS

        # push non-deliverables
        local.add(nondeliv)
        nondeliv = [os.path.split(x)[-1] for x in nondeliv]
        local.commit('NON-DELIVERABLE: ' + ', '.join(nondeliv))
        local.push(branch)

        if len(invalid) > 0:
            # commit only invalid metadata to github
            local.add([x.metapath for x in invalid])
            local.commit('INVALID: ' + ', '.join([x.name for x in invalid]))
            local.push(branch)
            return False

        else:
            # commit all deliverable to github
            local.add([x.metapath for x in valid])
            local.add([x.fullpath for x in valid])
            local.commit('VALID: ' + ', '.join([x.name for x in valid]))
            local.push(branch)

            title = '{user} attempts to publish valid deliverables to dev'
            title = title.format(user=branch)
            body = []
            body.append('publisher: **{user}**')
            bpdy.append('deliverables:')
            body.extend(['\t' + x.name for x in valid])
            body.append('assets:')
            body.extend(['\t' + x for x in nondeliv])
            body = '\n'.join(body)
            body = body.format(user=branch)

            num = client.create_pull_request(title, branch, 'dev', body=body)
            client.merge_pull_request(num, 'Publish authorized')

            return True

    def delete(self, name, from_server, from_local):
        '''
        Deletes a nerve project

        Args:
            name (str): name of project
            from_server (bool): delete Github project
            from_local (bool): delete local project directory

        Returns:
            bool: success status
        '''
        project = os.path.join(self['project-root'], name)

        if from_server:
            self._get_client(name).delete()
            # TODO: add git lfs logic for deletion
        if from_local:
            if os.path.split(project)[-1] == name:
                shutil.rmtree(project)
            else:
                warn(project + ' is not a project directory.  Local deletion aborted.')
                return False
        return True
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
