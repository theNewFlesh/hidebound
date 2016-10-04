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
# ------------------------------------------------------------------------------

class Nerve(object):
    def __init__(self, config):
        # TODO: add validation to config
        if isinstance(config, str):
            with open(config, 'r') as f:
                config = yaml.load(f)
        # TODO: add config validation via schematics
        self._config = config

    def __getitem__(self, key):
        return self._config[key]

    def _create_subdirectories(self, project):
        for subdir in chain(self['assets'], self['deliverables']):
            path = os.path.join(project, subdir)
            os.mkdir(path)
            # git won't commit empty directories
            open(os.path.join(path, '.keep'), 'w').close()

    def _create_metadata(self, project, name, project_id, url, version=1):
        config = deepcopy(self._config)
        del config['token']
        config['project-name'] = name
        config['project-id'] = project_id
        config['url'] = url
        config['version'] = 1
        # config['uuid'] = None
        with open(os.path.join(project, name + '_meta.yml'), 'w') as f:
            f.write(yaml.dump(config))

    def _get_client(self, name):
        config = self.config
        config['name'] = name
        return Client(config)

    def _get_project_and_branch(self, name, branch):
        project = os.path.join(self['project-root'], name)
        if branch == 'user-branch':
            branch = self['user-branch']
        return project, branch
    # --------------------------------------------------------------------------

    @property
    def config(self):
        return deepcopy(self._config)

    def create(self, name):
        '''
        create nerve project
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
        client.has_branch('dev', wait=True)
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
        clone nerve project
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
        request nerve deliverables
        '''
        project, branch = self._get_project_and_branch(name, branch)

        # TODO: ensure pulls only come from dev branch
        if include == []:
            include = self['request-include-patterns']
        if exclude == []:
            exclude = self['request-exclude-patterns']

        client = self._get_client(name)
        title = '{user} attempts to request deliverables from dev'
        title = title.format(user=self['user-branch'])
        # body = fancy markdown detailing request?
        num = client.create_pull_request(title, branch, 'dev')
        # additional dev to user-branch logic here if needed
        # if used/implemented propely merge-conflict logic will not be necessary
        # here
        client.merge_pull_request(num, 'Request authorized')

        Git(project, branch=branch).pull()
        GitLFS(project).pull(include, exclude)

        return True

    def publish(self, name, branch='user-branch', include=[], exclude=[], verbosity=0):
        '''
        publish nerve assets
        '''
        project, branch = self._get_project_and_branch(name, branch)
        wrn = False
        if verbosity > 0:
            wrn = True
        if include == []:
            include = self['publish-include-patterns']
        if exclude == []:
            exclude = self['publish-exclude-patterns']
        # ----------------------------------------------------------------------

        # PULL METADATA FROM DEV

        # pulling metadata first avoids merge conflicts
        # by setting HEAD to the most current
        # TODO: add branch checking logic to skip the following if not needed?

        client = self._get_client(name)
        title = 'Ensuring {branch} is up to date with dev'.format(branch=branch)
        # body = fancy markdown detailing publish?
        num = client.create_pull_request(title, 'dev', branch)
        # additional user-branch to dev logic here if needed
        # if used/implemented propely merge-conflict logic will not be necessary
        # here
        client.merge_pull_request(num, 'Update complete')
        local = Git(project)
        local.pull()
        # ----------------------------------------------------------------------

        # GET DATA

        # get only added assets
        lfs = GitLFS(project)
        assets = lfs.status(include=include, exclude=exclude, states=['added'], warnings=wrn)
        assets = [x['filepath'] for x in assets]
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
            meta = Metadata(asset)
            if meta.deliverable:
                if meta.valid:
                    valid.append(meta)
                else:
                    invalid.append(meta)
                meta.write()
            else:
                nondeliv.append(asset)
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
        deletes nerve project
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
