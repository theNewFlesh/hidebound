#! /usr/bin/env python
'''
The model module contains the Nerve class, the central component of the entire
nerve framework.

Platforrm:
    Unix

Author:
    Alex Braun <alexander.g.braun@gmail.com> <http://www.alexgbraun.com>
'''
# ------------------------------------------------------------------------------

from collections import defaultdict
from itertools import chain
import os
from pprint import pformat
import shutil
from warnings import warn
from schematics.exceptions import ValidationError
from nerve.core.git import Git
from nerve.core.git_lfs import GitLFS
from nerve.core.client import Client
from nerve.core.metadata import Metadata
from nerve.core.errors import KeywordError
# ------------------------------------------------------------------------------

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
        self.__config = config
    # --------------------------------------------------------------------------

    def __getitem__(self, key):
        return self.config[key]

    def __repr__(self):
        return pformat(self.config)

    def __get_config(self, config):
        output = self.config
        if config != {}:
            if 'project' in config.keys() and 'project' in output.keys():
                project = output['project']
                project.update(config['project'])
                config['project'] = project
            output.update(config)
            output = Metadata(output)
            try:
                output.validate()
            except ValidationError as e:
                raise KeywordError(e)
            output = output.data
        return output

    def _get_info(self, name, notes, config):
        config = self.__get_config(config)

        states = config['status-states']
        asset_types = config['status-asset-types']
        branch = config['user-branch']
        verbosity = config['verbosity']

        project = config['project']

        if name == None:
            name = project['project-name']
        if notes == None:
            notes = project['notes']

        project['project-name'] = name
        project['notes'] = notes

        path = os.path.join(config['project-root'], name)

        client_conf = dict(
            username=config['username'],
            token=config['token'],
            organization=config['organization'],
            project_name=project['project-name'],
            private=project['private'],
            url_type=config['url-type'],
            specification='client'
        )

        return config, project, name, path, states, asset_types, branch, verbosity, client_conf, notes

    @property
    def config(self):
        '''
        dict: copy of this object's configuration
        '''
        return self.__config.data
    # --------------------------------------------------------------------------

    def status(self, name=None, **config):
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
        config, _, _, path, states, asset_types, _, verbosity, client_conf, _ = self._get_info(name, None, config)

        warn_ = False
        if verbosity == 2:
            warn_ = True

        local = Git(path)
        local.add(all=True) # git lfs cannot get the status of unstaged files
        lfs = GitLFS(path)
        files = lfs.status(
            include=config['publish-include-patterns'],
            exclude=config['publish-exclude-patterns'],
            warnings=warn_
        )
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
        lut = {
                True: 'deliverable',
                False: 'nondeliverable'
        }
        for asset, v in sorted(temp.items()):
            if states:
                rogue_states = set(v['state']).difference(states)
                if len(rogue_states) > 0:
                    if verbosity > 0:
                        warn(asset + ' contains files of state: ' + ','.join(rogue_states))
                    continue

            output = Metadata(asset)
            atype = lut[output.data['deliverable']]
            if atype in asset_types:
                yield output

    def create(self, name=None, notes=None, **config):
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

        .. todo::
            - send data to DynamoDB
        '''
        # create repo
        config, project, name, path, _, _, _, verbosity, client_conf, _ = self._get_info(name, notes, config)

        client = Client(client_conf)
        local = Git(path, url=client['url'])
        # ----------------------------------------------------------------------

        # configure repo
        lfs = GitLFS(path)
        lfs.install(skip_smudge=True)
        lfs.create_config('http://localhost:8080')
        lfs.track(['*.' + x for x in project['lfs-extensions']])
        local.create_gitignore(project['gitignore'])
        # ----------------------------------------------------------------------

        # ensure first commit is on master branch
        local.add(all=True)
        local.commit('initial commit')
        local.push('master')
        # ----------------------------------------------------------------------

        # create project structure
        local.branch('dev')
        for subdir in chain(project['deliverables'], project['nondeliverables']):
            _path = os.path.join(path, subdir)
            os.mkdir(_path)
            # git won't commit empty directories
            open(os.path.join(_path, '.keep'), 'w').close()
        # ----------------------------------------------------------------------

        # create project metadata
        project['project-id'] = client['id']
        project['url'] = client['url']
        project['version'] = 1
        meta = project['specification'] + '_meta.yml' # implicit versioning
        meta = Metadata(project, metapath=meta)
        meta.validate()
        meta.write(validate=False)
        # ----------------------------------------------------------------------

        # commit everything
        local.add(all=True)
        local.commit(
            'VALID: {} created according to {} specification'.format(
                name,
                project['specification']
            )
        )
        local.push('dev')
        client.has_branch('dev')
        client.set_default_branch('dev')

        # cleanup
        shutil.rmtree(path)
        # ----------------------------------------------------------------------

        # add teams
        for team, perm in project['teams'].items():
            client.add_team(team, perm)

        return True

    def clone(self, name=None, **config):
        '''
        Clones a nerve project to local project-root directory

        Ensures given branch is present in the repository

        Args:
            project (str): name of project
            branch (str, optional): branch to clone from. Default: user's branch

        Returns:
            bool: success status

        .. todo::
            - catch repo already exists errors and repo doesn't exist errors
        '''
        config, _, _, path, _, _, branch, verbosity, _, _ = self._get_info(name, None, config)

        client = Client(client_conf)
        if client.has_branch(branch):
            local = Git(path, url=client['url'], branch=branch)
        else:
            local = Git(path, url=client['url'], branch='dev')

            # this done in lieu of doing it through github beforehand
            local.branch(branch)
            local.push(branch)

        return True

    def request(self, name=None, **config):
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
        config, _, _, path, _, _, branch, verbosity, _, _ = self._get_info(name, None, config)

        Git(path, branch=branch).pull('dev', branch)
        GitLFS(path).pull(
            config['request-include-patterns'],
            config['request-exclude-patterns']
        )

        return True
    # --------------------------------------------------------------------------

    def publish(self, name=None, notes=None, **config):
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

        .. todo::
            - add branch checking logic to skip the following if not needed?
        '''
        config, _, _, path, _, _, branch, verbosity, client_conf, _ = self._get_info(name, notes, config)

        # pulling metadata first avoids merge conflicts by keeping the
        # user-branch HEAD ahead of the dev branch
        local = Git(path, branch=branch)
        local.pull('dev', 'dev')
        local.merge('dev', branch)

        # get nondeliverable assets
        nondeliverables = self.status(status_asset_types=['nondeliverable'], **config)
        nondeliverables = list(nondeliverables)

        # publish nondeliverables
        if len(nondeliverables) > 0:
            # push non-deliverables to user-branch
            local.add([x.datapath for x in nondeliverables])
            names = [x['asset-name'] for x in nondeliverables]
            local.commit('NON-DELIVERABLES: ' + ', '.join(names))
            local.push(branch)
        # ----------------------------------------------------------------------

        # get only added deliverable assets
        deliverables = self.status(
            status_states=['added'],
            status_asset_types=['deliverable'],
            **config
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

        client = Client(client_conf)

        if len(invalid) > 0:
            # commit only invalid metadata to github user branch
            local.add([x.metapath for x in invalid])
            local.commit('INVALID: ' + ', '.join([x['asset-name'] for x in invalid]))
            local.push(branch)
            return False

        else:
            # commit all deliverable data and metadata to github dev branch
            local.add([x.metapath for x in valid])
            local.add([x.datapath for x in valid])
            names = [x['asset-name'] for x in valid]
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
    # --------------------------------------------------------------------------

    def delete(self, from_server, from_local, name=None, **config):
        '''
        Deletes a nerve project

        Args:
            project (str): name of project
            from_server (bool): delete Github project
            from_local (bool): delete local project directory

        Returns:
            bool: success status

        .. todo::
            - add git lfs logic for deletion
        '''
        _, _, _, path, _, _, _, verbosity, client_conf, _ = self._get_info(name, None, config)
        if from_server:
            Client(client_conf).delete()
            # git lfs deletion logic
        if from_local:
            if os.path.split(path)[-1] == name:
                shutil.rmtree(path)
            else:
                warn(path + ' is not a project directory.  Local deletion aborted.')
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
