#! /usr/bin/env python
from copy import deepcopy
from collections import defaultdict
from itertools import chain
import os
import shutil
from warnings import warn
import yaml
from schematics.exceptions import ValidationError
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
        create, clone, request, publish, delete and __getitem__
    '''
    def __init__(self, config):
        '''
        Nerve constructor that takes a nerverc configuration (yaml format)

        Args:
            config (str or dict): a fullpath to a nerverc config or a dict of one

        Returns:
            Nerve
        '''
        config = Metadata(config)
        config.validate()
        self._config = config.data

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
        config['version'] = version
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

    def status(self, project, include=[], exclude=[], states=[], verbosity=0,
                asset_type=['deliverable', 'nondeliverable']):
        '''
        Reports on the status of all affected files within a given project

        Args:
            project (str): name of project
            include (list, optional): list of regular expressions user to include specific assets
            exclude (list, optional): list of regular expressions user to exclude specific assets
            states (list, optional): list of object states files are allowed to be in.
                options include: added, copied, deleted, modified, renamed, updated and untracked
            verbosity (int, optional): level of verbosity for output. Default: 0
                options include: 0, 1 and 2

        Yields:
            Metadata: Metadata object of each asset
        '''
        warn_ = False
        if verbosity == 2:
            warn_ = True
        if len(include) == 0:
            include = self['publish-include-patterns']
        if len(exclude) == 0:
            exclude = self['publish-exclude-patterns']

        local = Git(project)
        local.add(all=True) # git lfs cannot get the status of unstaged files
        lfs = GitLFS(project)
        files = lfs.status(include=include, exclude=exclude, warnings=warn_)
        # ----------------------------------------------------------------------

        temp = defaultdict(lambda: defaultdict(lambda: []))
        for file in files:
            asset = file['fullpath'].split(os.sep)
            if len(asset) > 2:
                asset = os.path.join(asset[0], asset[1])
            else:
                asset = file['fullpath']

            for k, v in file.items():
                temp[asset][k].append(v)

        local.reset()
        # ----------------------------------------------------------------------

        for asset, v in sorted(temp.items()):
            if states:
                rogue_states = set(v['state']).difference(states)
                if len(rogue_states) > 0:
                    if verbosity > 0:
                        warn(asset + ' contains files of state: ' + ','.join(rogue_states))
                    continue

            output = Metadata(asset)
            asset_type = [x is 'deliverable' for x in asset_type]
            if output.data.deliverable in asset_type:
                yield output

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

    def clone(self, project, branch='user-branch'):
        '''
        Clones a nerve project to local project-root directory

        Ensures given branch is present in the repository

        Args:
            project (str): name of project
            branch (str, optional): branch to clone from. Default: user's branch

        Returns:
            bool: success status
        '''
        # TODO: catch repo already exists errors and repo doesn't exist errors
        name = project
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

    def request(self, project, branch='user-branch', include=[], exclude=[]):
        '''
        Request deliverables from the dev branch of given project

        Args:
            project (str): name of project
            branch (str, optional): branch to pull deliverables into. Default: user's branch
            include (list, optional): list of regular expressions user to include specific deliverables
            exclude (list, optional): list of regular expressions user to exclude specific deliverables

        Returns:
            bool: success status
        '''
        name = project
        project, branch = self._get_project_and_branch(name, branch)

        if len(include) == 0:
            include = self['request-include-patterns']
        if len(exclude) == 0:
            exclude = self['request-exclude-patterns']

        Git(project, branch=branch).pull('dev', branch)
        GitLFS(project).pull(include, exclude)

        return True

    def _publish_non_deliverables(self, local, project, branch, include, exclude, verbosity):
        '''
        Convenience method for publishing non-deliverable assets to a github user branch

        Args:
            project (str): name of project
            branch (str): branch to pull deliverables from. Default: user's branch
            include (list): list of regular expressions user to include specific assets
            exclude (list): list of regular expressions user to exclude specific assets
            verbosity (int): level of events to print to stdout. Default: 0

        Returns:
            bool: success status
        '''
        # get nondeliverable assets
        nondeliverables = self.status(
            project,
            include=include,
            exclude=exclude,
            verbosity=verbosity,
            asset_type=['nondeliverable']
        )

        # push non-deliverables to user-branch
        local.add([x.datapath for x in nondeliverables])
        names = [x.name for x in nondeliverables]
        local.commit('NON-DELIVERABLES: ' + ', '.join(names))
        local.push(branch)

        return True

    def publish(self,
            project, branch='user-branch', include=[], exclude=[], verbosity=0):
        '''
        Attempt to publish deliverables from user's branch to given project's dev branch on Github

        All assets will be published to the user's branch.
        If all deliverables are valid then all data and metadata will be commited
        to the user's branch and merged into the dev branch.
        If not only invalid metadata will be commited to the user's branch

        Args:
            project (str): name of project
            branch (str, optional): branch to pull deliverables from. Default: user's branch
            include (list, optional): list of regular expressions user to include specific assets
            exclude (list, optional): list of regular expressions user to exclude specific assets
            verbosity (int, optional): level of events to print to stdout. Default: 0

        Returns:
            bool: success status
        '''
        name = project
        project, branch = self._get_project_and_branch(name, branch)

        # pulling metadata first avoids merge conflicts
        # by setting HEAD to the most current
        # TODO: add branch checking logic to skip the following if not needed?
        local = Git(project)
        local.pull('dev', branch)

        self._publish_non_deliverables(
            local,
            project,
            branch=branch,
            include=include,
            exclude=exclude,
            verbosity=verbosity
        )
        # ----------------------------------------------------------------------

        # get only added deliverable assets
        deliverables = self.status(
            project,
            include=include,
            exclude=exclude,
            verbosity=verbosity,
            states=['added'],
            asset_type=['deliverable']
        )

        invalid = []
        valid = []
        for deliv in deliverables:
            deliv.get_traits()
            deliv.write()
            try:
                deliv.validate()
            except ValidationError as e:
                if verbosity > 0:
                    warn(e)
                invalid.append(deliv)
                continue
            valid.append(deliv)
        # ----------------------------------------------------------------------

        client = self._get_client(name)

        if len(invalid) > 0:
            # commit only invalid metadata to github user branch
            local.add([x.metapath for x in invalid])
            local.commit('INVALID: ' + ', '.join([x.name for x in invalid]))
            local.push(branch)
            return False

        else:
            # commit all deliverable data and metadata to github dev branch
            local.add([x.metapath for x in valid])
            local.add([x.datapath for x in valid])
            names = [x.name for x in valid]
            local.commit('VALID: ' + ', '.join(names))
            local.push(branch)

            title = '{user} attempts to publish valid deliverables to dev'
            title = title.format(user=branch)
            body = []
            body.append('publisher: **{user}**')
            body.append('deliverables:')
            body.extend(['\t' + x for x in names])
            body = '\n'.join(body)
            body = body.format(user=branch)

            num = client.create_pull_request(title, branch, 'dev', body=body)
            client.merge_pull_request(num, 'Publish authorized')

            return True

    def delete(self, project, from_server, from_local):
        '''
        Deletes a nerve project

        Args:
            project (str): name of project
            from_server (bool): delete Github project
            from_local (bool): delete local project directory

        Returns:
            bool: success status
        '''
        name = project
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
