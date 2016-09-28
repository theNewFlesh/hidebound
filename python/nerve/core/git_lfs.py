#! /usr/bin/env python
import os
from nerve.core.utils import execute_subprocess
import subprocess
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
        output = output.split('\n')[1:-1]
        output = [x.lstrip().split(' ') for x in output]
        return output

    def pull(self, include=[], exclude=[]):
        cmd = 'git lfs pull'
        if include != []:
            cmd += ' -I ' + ','.join(include)
        if exclude != []:
            cmd += ' -X ' + ','.join(exclude)

        execute_subprocess(cmd)

    @property
    def status(self):
        cmd = 'git lfs status --porcelain'
        status = execute_subprocess(cmd)
        lut = dict(
            A='new_file',
            D='deleted',
            M='modified',
            R='renamed'
        )

        for item in status:
            datum = {}
            datum['staged'] = False
            if item[0] != ' ':
                datum['staged'] = True
                datum['state'] = lut[item[0]]
            else:
                datum['state'] = lut[item[1]]
            datum['object'] = item[3:].split(' ')[0]
            yield datum
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
