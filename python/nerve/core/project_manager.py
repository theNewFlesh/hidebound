#! /usr/bin/env python
'''
The project_manager module contains the ProjectManager class.  This class is
used for creating, deleting and modifying Nerve projects.

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
import yaml
from schematics.exceptions import ValidationError
from nerve.core.utils import conform_keys, deep_update, Name
from nerve.core.metadata import Metadata
from nerve.core.errors import KeywordError
from nerve.core.project import Project
from nerve.core.git import Git
from nerve.core.git_lfs import GitLFS
from nerve.core.git_remote import GitRemote
# from nerve.core.logger import Logger
# ------------------------------------------------------------------------------

PROJECT_MANAGER_SPEC = 'conf001'
PROJECT_METADATA_RE = 'proj\d\d\d_meta'

class ProjectManager(object):
    '''
    Class for handling nerve projects

    Attributes:
        config (dict): a dictionary representing Nerve's internal configuration
        project_template (dict): a dictionary representing Nerve's internal project template

    API:
        create, clone, request, publish, delete, status, config and project_template

    Args:
        config (str or dict): a fullpath to a nerverc config or a dict of one

    Returns:
        Nerve
    '''
    def __init__(self, config):
        config = Metadata(config, spec=PROJECT_MANAGER_SPEC, skip_keys=['environment'])
        config.validate()
        config = config.data
        self._config = config

        # self._logger = Logger(log_level=config['log-level'])

        template = None
        if 'project-template' in config.keys():

            temppath = config['project-template']
            if os.path.exists(temppath):
                with open(temppath, 'r') as f:
                    template = yaml.load(f)

                proj_spec = template['specification']
                spec = Name(temppath).specification

                template = Metadata(template, spec=spec)
                template.validate()
                template = template.data
                template['specification'] = proj_spec
        self._project_template = template
    # --------------------------------------------------------------------------

    def __repr__(self):
        msg = 'CONFIG:\n'
        msg += pformat(self.config)
        msg += '\n\nPROJECT TEMPLATE:\n'
        msg += pformat(self.project_template)
        return msg

    def _log(self, result):
        '''
        Logging method
        '''
        # log = getattr(self._logger, result['log-level'])
        # return log(result['message'])
        return result

    def __get_project_metadata(self, dirpath, log_level='warn'):
        '''
        Finds project metadata given the directory the _meta.yml file resides in

        Args:
            dirpath (str): local project directory
            log_level (str, optional): logging level. Default: warn

        Returns:
            dict: project metadata

        Raises:
            OSError or warning

        '''
        if os.path.exists(dirpath):
            meta = os.listdir(dirpath)
            meta = list(filter(lambda x: re.search(PROJECT_METADATA_RE, x), meta))
            if len(meta) == 1:
                meta = meta[0]
                return meta

        msg = dirpath + ' project metadata does not exist'
        if log_level == 'error':
            raise OSError(msg)
        elif log_level == 'warn':
            warn(msg)
        return None

    def __get_config(self, config):
        '''
        Convenience method for creating a new temporary configuration dict by
        overwriting a copy of the internal config with keyword arguments
        specified in config

        Args:
            config (dict): dict of keyword arguments

        Returns:
            dict: new config
        '''
        output = self.config
        if config != {}:
            config = conform_keys(config)
            output = deep_update(output, config)
            output = Metadata(output, spec=PROJECT_MANAGER_SPEC, skip_keys=['environment'])
            try:
                output.validate()
            except ValidationError as e:
                raise KeywordError(e)
            output = output.data
        return output

    def __get_project_config(self, name, notes, config, project):
        '''
        Convenience method for creating a new temporary project dict by
        overwriting a copy of the internal project template, if it exists,
        with keyword arguments specified in project

        Args:
            name (str): name of project
            notes (str, None): notes to be added to metadata
            config (dict, None): config dictionary
            project (dict, None): config dictionary

        Returns:
            dict: project metadata
        '''
        project['project-name'] = name
        if notes != None:
            project['notes'] = notes

        if self._project_template != None:
            project = deep_update(self._project_template, project)

        return project

    def _get_info(self, name, notes='', config={}, project={}, log_level='warn'):
        '''
        Convenience method for creating new temporary config

        Args:
            name (str): name of project
            notes (str, optional): notes to be added to metadata. Default: ''
            config (dict, optional): config parameters, overwrites fields in a copy of self.config
            project (dict, optional): project metadata. Default: {}
            log_level (str, optional): logging level. Default: warn

        Returns:
            namedtuple: tuple with conveniently named attributes
        '''
        if not isinstance(name, str):
            raise TypeError('name argument must be a string')
        # ----------------------------------------------------------------------

        config = self.__get_config(config)

        project = self.__get_project_config(name, notes, config, project)
        if 'private' in project.keys():
            private = project['private']
        else:
            project['private'] = config['private']

        path = os.path.join(config['project-root'], project['project-name'])
        meta = self.__get_project_metadata(path, log_level=log_level)

        remote = {
            'username':      config['username'],
            'token':         config['token'],
            'organization':  config['organization'],
            'project-name':  name,
            'private':       project['private'],
            'url-type':      config['url-type'],
            'specification': 'remote'
        }
        # ----------------------------------------------------------------------

        # create info object
        Info = namedtuple('Info', ['config', 'project', 'remote', 'root', 'path', 'meta'])
        info = Info(config, project, remote, config['project-root'], path, meta)
        return info

    def _get_project(self, name):
        '''
        Convenience factory method for generating Project objects

        Args:
            name (str): name of project

        Returns:
            Project
        '''
        info = self._get_info(name)
        if info.meta:
            return Project(info.meta, info.remote, info.root)
        return None

    @property
    def config(self):
        '''
        dict: copy of this object's configuration
        '''
        return deepcopy(self._config)

    @property
    def project_template(self):
        '''
        dict: copy of this object's project template
        '''
        return deepcopy(self._project_template)
    # --------------------------------------------------------------------------

    def create(self, name, notes=None, config={}, **project):
        '''
        Creates a nerve project on Github and in the project-root folder

        Created items include:
            Github repository
            dev branch
            nerve project structure
            .lfsconfig
            .gitattributes
            .gitignore
            .git-credentials

        Args:
            name (str): name of project. Default: None
            notes (str, optional): notes to appended to project metadata. Default: None
            config (dict, optional): config parameters, overwrites fields in a copy of self.config
            \**project: optional project parameters, overwrites fields in a copy of self.project_template

        Returns:
            bool: success status

        .. todo::
            - fix whetever causes the notebook kernel to die
            - send data to DynamoDB
        '''
        info = self._get_info(name, notes, config, project)
        config = info.config
        project = info.project
        path = info.path

        # project = Project(info.meta, info.remote, info.root)
        # project.create(info.config, **info.project)
        # return self._log(result)

        # create repo
        remote = GitRemote(info.remote)
        local = Git(path, url=remote['url'], environment=config['environment'])
        # ----------------------------------------------------------------------

        # configure repo
        lfs = GitLFS(path, environment=config['environment'])
        lfs.install(skip_smudge=True)
        lfs.create_config(config['lfs-server-url'])
        lfs.track(['*.' + x for x in project['lfs-extensions']])

        local.create_gitignore(project['gitignore'])
        local.create_git_credentials(config['git-credentials'])
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
        project['project-id'] = remote['id']
        project['project-url'] = remote['url']
        project['version'] = 1
        meta = '_'.join([
            project['project-name'],
            project['specification'],
            'meta.yml'
        ]) # implicit versioning
        meta = Metadata(project, metapath=meta, skip_keys=['environment'])
        meta.validate()
        meta.write(validate=False)
        # ----------------------------------------------------------------------

        # commit everything
        local.add(all=True)
        local.commit(
            'VALID PROJECT:\n\t{} created according to {} specification'.format(
                project['project-name'],
                project['specification']
            )
        )
        local.push('dev')
        remote.has_branch('dev', timeout=config['timeout'])
        remote.set_default_branch('dev')

        # add teams
        for team, perm in project['teams'].items():
            remote.add_team(team, perm)
        # ----------------------------------------------------------------------

        # cleanup
        os.chdir(config['project-root'])
        shutil.rmtree(path) # problem if currently in path

        return True

    def clone(self, name, **config):
        '''
        Clones a nerve project to local project-root directory

        Ensures given branch is present in the repository

        Args:
            name (str): name of project. Default: None
            `**config`: optional config parameters, overwrites fields in a copy of self.config

        **ConfigParameters:
            * **log_level** (int): level of log-level for output. Default: 0
            * **user_branch** (str): branch to clone from. Default: user's branch

        Returns:
            bool: success status

        .. todo::
            - catch repo already exists errors and repo doesn't exist errors
        '''
        info = self._get_info(name, config=config, log_level=None)
        config = info.config

        remote = GitRemote(info.remote)
        if remote.has_branch(config['user-branch'], timeout=config['timeout']):
            local = Git(
                info.path,
                url=remote['url'],
                branch=config['user-branch'],
                environment=config['environment']
            )
        else:
            local = Git(
                info.path,
                url=remote['url'],
                branch='dev',
                environment=config['environment']
            )

            # this done in lieu of doing it through github beforehand
            local.branch(config['user-branch'])
            local.push(config['user-branch'])

        info = self._get_info(name, config=config)
        project = Project(info.meta, info.remote, info.root)

        return True

    def status(self, name, **config):
        '''
        Reports on the status of all affected files within a given project

        Args:
            name (str): name of project. Default: None
            `**config`: optional config parameters, overwrites fields in a copy of self.config

        **ConfigParameters:
            * **status_include_patterns** (list): list of regular expressions user to include specific assets
            * **status_exclude_patterns** (list): list of regular expressions user to exclude specific assets
            * **status_states** (list): list of object states files are allowed to be in.
              Options: added, copied, deleted, modified, renamed, updated and untracked
            * **log_level** (int): level of log-level for output. Default: 0


        Yields:
            Metadata: Metadata object of each asset
        '''
        info = self._get_info(name, config=config)

        project = Project(info.meta, info.remote, info.root)
        result = project.status(info.config)

        self._log(result)
        return result

    def request(self, name, **config):
        '''
        Request deliverables from the dev branch of given project

        Args:
            name (str): name of project. Default: None
            `**config`: optional config parameters, overwrites fields in a copy of self.config

        **ConfigParameters:
            * **user_branch** (str): branch to pull deliverables into. Default: user's branch
            * **request_include_patterns** (list): list of regular expressions user to include specific deliverables
            * **request_exclude_patterns** (list): list of regular expressions user to exclude specific deliverables
            * **log_level** (int): level of log-level for output. Default: 0

        Returns:
            bool: success status
        '''
        info = self._get_info(name, config=config)
        project = Project(info.meta, info.remote, info.root)
        result = project.request(info.config)

        return self._log(result)

    def publish(self, name, notes=None, **config):
        '''
        Attempt to publish deliverables from user's branch to given project's dev branch on Github

        All assets will be published to the user's branch.
        If all deliverables are valid then all data and metadata will be commited
        to the user's branch and merged into the dev branch.
        If not only invalid metadata will be commited to the user's branch

        Args:
            name (str): name of project. Default: None
            notes (str, optional): notes to appended to project metadata. Default: None
            `**config`: optional config parameters, overwrites fields in a copy of self.config

        **ConfigParameters:
            * **user_branch** (str): branch to pull deliverables from. Default: user's branch
            * **publish_include_patterns** (list): list of regular expressions user to include specific assets
            * **publish_exclude_patterns** (list): list of regular expressions user to exclude specific assets
            * **log_level** (int): level of log-level for output. Default: 0

        Returns:
            bool: success status

        .. todo::
            - add branch checking logic to skip the following if not needed?
        '''
        info = self._get_info(name, notes, config)
        project = Project(info.meta, info.remote, info.root)
        result = project.publish(info.config, notes=notes)

        return self._log(result)
    # --------------------------------------------------------------------------

    def delete(self, name, from_server, from_local, **config):
        '''
        Deletes a nerve project

        Args:
            name (str): name of project. Default: None
            from_server (bool): delete Github project
            from_local (bool): delete local project directory
            `**config`: optional config parameters, overwrites fields in a copy of self.config

        **ConfigParameters:
            * **log_level** (int): level of log-level for output. Default: 0

        Returns:
            bool: success status

        .. todo::
            - add git lfs logic for deletion
        '''
        info = self._get_info(name, config=config)

        if from_server:
            GitRemote(info.remote).delete()
            # git lfs deletion logic
        if from_local:
            # if os.path.split(self.project_path)[-1] == self.config['project-name']:
            if os.path.exists(info.path):
                shutil.rmtree(info.path)
            else:
                warn(info.path + ' is not a project directory.  Local deletion aborted.')
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

__all__ = ['ProjectManager']

if __name__ == '__main__':
    main()
