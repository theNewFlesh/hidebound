#! /usr/bin/env python
'''
The project module contains the Project class, which represent a single Nerve
project.  This in turn represents a single git repo, Github repo and directory
within a bucket on AWS.

Platforrm:
    Unix

Author:
    Alex Braun <alexander.g.braun@gmail.com> <http://www.alexgbraun.com>
'''
# ------------------------------------------------------------------------------

from collections import defaultdict, namedtuple
from copy import deepcopy
from itertools import chain
import os
from pprint import pformat
import re
import shutil
from warnings import warn
from schematics.exceptions import ValidationError
from nerve.core.metadata import Metadata
from nerve.core.git import Git
from nerve.core.git_lfs import GitLFS
from nerve.core.git_remote import GitRemote
# ------------------------------------------------------------------------------

class Project(object):
    '''
    This class provides an API to an already locally existing Nerve project

    Attributes:
        metadata (dict): a dictionary representing this project's metadata
        project_path (str): the fullpath of this project
        remote_config (dict): a configuration to be passed to the git remote client

    API:
        request, publish, status, metadata, project_path and remote_config

    Args:
        fullpath (str): fullpath to project's local metadata (_meta.yml) file
        remote_config (str or dict): a fullpath to a GitRemote config or a dict of one
        project_root (str): fullpath to local root directory for all Nerve projects

    Returns:
        Nerve
    '''
    def __init__(self, fullpath, remote_config, project_root):
        meta = Metadata(fullpath, skip_keys=['environment'])
        meta.validate()
        self._metadata = meta.data
        self._project_path = os.path.join(project_root, meta['project-name'])
        self._remote_config = remote_config
    # --------------------------------------------------------------------------

    def __repr__(self):
        msg = 'PROJECT PATH:\n'
        msg += self.project_path
        msg += '\n\nPROJECT METADATA:\n'
        msg += pformat(self.metadata)
        msg += '\n\nREMOTE CONFIG:\n'
        msg += pformat(self.remote_config)
        return msg

    @property
    def metadata(self):
        '''
        dict: copy of this object's configuration
        '''
        return deepcopy(self._metadata)

    @property
    def remote_config(self):
        '''
        dict: copy of this object's project template
        '''
        return deepcopy(self._remote_config)

    @property
    def project_path(self):
        '''
        dict: copy of this object's project path
        '''
        return deepcopy(self._project_path)
    # --------------------------------------------------------------------------

    def status(self, config):
        '''
        Reports on the status of all affected files within a given project

        Args:
            config: ProjectManager config

        ConfigParameters:
            * **status-include-patterns** *(list)*: list of regular expressions user to include specific assets
            * **status-exclude-patterns** *(list)*: list of regular expressions user to exclude specific assets
            * **status-states** *(list)*: list of object states files are allowed to be in.
              Options: added, copied, deleted, modified, renamed, updated and untracked
            * **log-level** *(str)*: logging level

        Yields:
            Metadata: Metadata object of each asset
        '''

        warn_ = False
        if config['log-level'] == 2:
            warn_ = True

        local = Git(self.project_path, environment=config['environment'])
        local.reset()
        local.add(all=True) # git lfs cannot get the status of unstaged files
        lfs = GitLFS(self.project_path, environment=config['environment'])
        files = lfs.status(
            include=config['status-include-patterns'],
            exclude=config['status-exclude-patterns'],
            warnings=warn_
        )
        # ----------------------------------------------------------------------

        # aggregate the data into prototype pattern (unique keys with list values)
        agg = defaultdict(lambda: defaultdict(lambda: []))
        for file in files:
            asset = file['path'].split(os.sep)
            if len(asset) > 2:
                asset = os.path.join(asset[0], asset[1])
                asset = re.search('.*' + asset, file['fullpath'])
                asset = asset.group(0)
            else:
                asset = file['fullpath']

            for k, v in file.items():
                agg[asset][k].append(v)

        local.reset()
        # ----------------------------------------------------------------------

        for asset, asset_data in sorted(agg.items()):
            if config['status-states']:
                rogue_states = set(asset_data['state'])
                rogue_states = rogue_states.difference(config['status-states'])
                if len(rogue_states) > 0:
                    if config['log-level'] > 0:
                        warn(asset + ' contains files of state: ' + ','.join(rogue_states))
                    continue

            output = Metadata(asset)
            if output.data['asset-type'] in config['status-asset-types']:
                output.get_traits()
                yield output

    def request(self, config):
        '''
        Request deliverables from the dev branch of given project

        Args:
            config: ProjectManager config

        ConfigParameters:
            * **user-branch** *(str)*: branch to pull deliverables into. Default: user's branch
            * **request-include-patterns** *(list)*: list of regular expressions user to include specific deliverables
            * **request-exclude-patterns** *(list)*: list of regular expressions user to exclude specific deliverables
            * **log-level** *(str)*: logging level

        Returns:
            bool: success status
        '''
        self._update_local(config)
        lfs = GitLFS(self.project_path, environment=config['environment'])
        lfs.pull(
            config['request-include-patterns'],
            config['request-exclude-patterns']
        )

        return True
    # --------------------------------------------------------------------------

    def _update_local(self, config):
        '''
        Convenience method for merging remote dev branch into local user branch

        Ensures non-fastforward merge conflicts don't occur

        Args:
            config (dict): ProjectManager config

        ConfigParameters:
            * **user-branch** *(str)*: branch to pull deliverables into. Default: user's branch
            * **environment** *(dict)*: environment variables used for calls to shell

        Returns:
            None
        '''
        # pulling metadata first avoids merge conflicts by keeping the
        # user-branch HEAD ahead of the dev branch
        local = Git(
            self.project_path,
            branch=config['user-branch'],
            environment=config['environment']
        )
        local.branch('dev')
        local.pull('dev')
        local.branch(config['user-branch'])
        local.merge('dev', config['user-branch'])

    def _publish_nondeliverables(self, config):
        '''
        Convenience method for publishing nondeliverable assets

        Assets published to user branch

        Args:
            config (dict): ProjectManager config

        ConfigParameters:
            * **user-branch** *(str)*: branch to pull deliverables into. Default: user's branch
            * **environment** *(dict)*: environment variables used for calls to shell

        Returns:
            None
        '''
        # get nondeliverable assets
        config['status-asset-types'] = ['nondeliverable']
        nondeliverables = list(self.status(config))
        for non in nondeliverables:
            non.get_traits()
            non.write(validate=False)

        # publish nondeliverables
        if len(nondeliverables) > 0:
            lfs = GitLFS(self.project_path, environment=config['environment'])
            local = Git(
                self.project_path,
                branch=config['user-branch'],
                environment=config['environment']
            )

            # push non-deliverables to user-branch
            local.add([x.metapath for x in nondeliverables])
            local.add([x.datapath for x in nondeliverables])

            message = [x['asset-name'] for x in nondeliverables]
            message = '\n\t'.join(message)
            message = 'NON-DELIVERABLES:\n\t' + message
            local.commit(message)

            local.push(config['user-branch'])

    def _get_deliverables(self, config):
        '''
        Convenience method for retrieving valid and invalid deliverable assets

        Args:
            config (dict): ProjectManager config

        ConfigParameters:
            * **log-level** *(str)*: logging level

        Returns:
            tuple: valid deliverables, invalid deliverables
        '''
        # get only added deliverable assets
        config['status-states'] = ['added']
        config['status-asset-types'] = ['deliverable']
        deliverables = self.status(config)

        invalid = []
        valid = []
        for deliv in deliverables:
            deliv.get_traits()
            deliv.write()
            try:
                deliv.validate()
            except ValidationError as e:
                if config['log-level'] > 0:
                    warn(e)
                invalid.append(deliv)
                continue
            valid.append(deliv)

        return valid, invalid

    def publish(self, config, notes=None):
        '''
        Attempt to publish deliverables from user's branch to given project's dev branch on Github

        All assets will be published to the user's branch.
        If all deliverables are valid then all data and metadata will be commited
        to the user's branch and merged into the dev branch.
        If not only invalid metadata will be commited to the user's branch

        Args:
            config: ProjectManager config
            notes (str, optional): notes to appended to project metadata. Default: None

        ConfigParameters:
            * **user-branch** *(str)*: branch to pull defrom kaiverables from. Default: user's branch
            * **publish-include-patterns** *(list)*: list of regular expressions user to include specific assets
            * **publish-exclude-patterns** *(list)*: list of regular expressions user to exclude specific assets
            * **log-level** *(str)*: logging level

        Returns:
            bool: success status

        .. todo::
            - add branch checking logic to skip the following if not needed?
        '''
        self._publish_nondeliverables(config)
        self._update_local(config)
        valid, invalid = self._get_deliverables(config)
        # ----------------------------------------------------------------------

        remote = GitRemote(self.remote_config)
        local = Git(
            self.project_path,
            branch=config['user-branch'],
            environment=config['environment']
        )
        lfs = GitLFS(self.project_path, environment=config['environment'])

        if len(invalid) > 0:
            # commit only invalid metadata to github user branch
            local.add([x.metapath for x in invalid])

            message = [x['asset-name'] for x in invalid]
            message = '\n\t'.join(message)
            message = 'INVALID DELIVERABLES:\n\t' + message
            local.commit(message)

            local.push(config['user-branch'])
            return False

        else:
            # commit all deliverable data and metadata to github dev branch
            local.add([x.metapath for x in valid])
            local.add([x.datapath for x in valid])

            names = [x['asset-name'] for x in valid]
            message = '\n\t'.join(names)
            message = 'VALID DELIVERABLES:\n\t' + message
            local.commit(message)

            local.push(config['user-branch'])

            title = '{user} attempts to publish valid deliverables to dev'
            title = title.format(user=config['user-branch'])
            body = []
            body.append('publisher: **{user}**')
            body.append('deliverables:')
            body.extend(['\t' + x for x in names])
            body = '\n'.join(body)
            body = body.format(user=config['user-branch'])

            sha = local.sha
            remote_sha = remote.get_head_sha(config['user-branch'])
            while sha != remote_sha:
                remote_sha = remote.get_head_sha(config['user-branch'])

            # this produces a race condition with the local.push process
            num = remote.create_pull_request(
                title,
                'dev',
                config['user-branch'],
                body=body
            )
            remote.merge_pull_request(num, 'Publish authorized')

            return True
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

__all__ = ['Project']

if __name__ == '__main__':
    main()
