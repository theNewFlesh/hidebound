#! /usr/bin/env python
import os
from configparser import ConfigParser
from nerve.core.utils import execute_subprocess, status
# ------------------------------------------------------------------------------

class GitLFS(object):
    def __init__(self, working_dir):
        self._working_dir = working_dir
        os.chdir(working_dir)
        # start server
        # execute_subprocess('git-lfs-s3')

    @property
    def working_dir(self):
        return self._working_dir

    def create_config(self, url, access='basic'):
        '''
        write .lfsconfig file
        '''
        lfsconfig = ConfigParser()
        lfsconfig.add_section('lfs')
        lfsconfig.set('lfs', 'url', url)
        lfsconfig.set('lfs', 'access', access)
        path = os.path.join(self._working_dir, '.lfsconfig')
        with open(path, 'w') as f:
            lfsconfig.write(f)

        return os.path.exists(path)

    def install(self, force=False, local=False, skip_smudge=False):
        '''
        runs git lfs install
        check .git/hooks for pre-push
        '''
        cmd = 'git lfs install'
        # --system ommitted
        if force:
            cmd += ' --force'
        if local:
            cmd += ' --local'
        if skip_smudge:
            cmd += ' --skip-smudge'

        return execute_subprocess(cmd)

    def track(self, expressions=[]):
        '''
        runs git lfs track
        '''
        if isinstance(expressions, str):
            expressions = [expressions]
        cmd = 'git lfs track'
        for exp in expressions:
            execute_subprocess(cmd + ' ' + exp)

        output = execute_subprocess(cmd, 'no matches found:.*')
        output = [x.lstrip().split(' ') for x in output[1:-1]]
        return output

    def pull(self, include=[], exclude=[]):
        cmd = 'git lfs pull'
        if include != []:
            cmd += ' -I ' + ','.join(include)
        if exclude != []:
            cmd += ' -X ' + ','.join(exclude)

        return execute_subprocess(cmd)

    def status(self, path_re=None, states=[], staged=None, warnings=False):
        return status(
            'git lfs status --porcelain',
            path_re=path_re,
            states=states,
            staged=staged
        )
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

__all__ = ['GitLFS']

if __name__ == '__main__':
    main()
