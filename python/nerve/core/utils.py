#! /usr/bin/env python
import re
from warnings import warn
from subprocess import Popen, PIPE, STDOUT, SubprocessError
# ------------------------------------------------------------------------------

def execute_subprocess(command, error_re='Error:.*'):
    output = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
    stderr = output.stderr.read().decode('utf-8')
    output = output.stdout.readlines()
    output = [x.decode('utf-8').strip('\n') for x in output]

    err = '\n'.join(output)
    for e in [err, stderr]:
        error = re.search(error_re, e)
        if error:
            message = 'Command: "' + command
            message += '" returned "' + error.group(0) + '"'
            raise SubprocessError(message)

    return output

def status(self, command, path_re=None, states=[], staged=None, warnings=False):
    status = execute_subprocess(command)
    lut = {
        'A': 'added',
        'C': 'copied',
        'D': 'deleted',
        'M': 'modified',
        'R': 'renamed',
        'U': 'updated',
        '?': 'untracked'
    }

    if path_re:
        path_re = re.compile(path_re)
    # ----------------------------------------------------------------------

    # for item in self._repo.index.diff('HEAD', R=True):
    #     output = dict(
    #         filepath=item.a_path, # is this always correct?
    #         state=lut[item.change_type],
    #         staged=True
    #     )
    for item in status:
        output = {}
        output['staged'] = False
        if item[0] != ' ':
            output['staged'] = True
            output['state'] = lut[item[0]]
        else:
            output['state'] = lut[item[1]]
        filepath = item[3:].split(' ')[0]
        output['filepath'] = filepath
        # ------------------------------------------------------------------

        message = None
        _states = states[0]
        if len(states) > 1:
            _states = ', '.join(states[:-1]) + ' or ' + states[-1]

        if path_re:
            found = path_re.search(filepath)
            if not found:
                message = filepath + ' is excluded'
        if states:
            if output['state'] not in states:
                message = filepath + ' is not ' + _states
        if staged != None:
            if output['staged'] != staged:
                if staged:
                    message = filepath + ' is unstaged'
                else:
                    message = filepath + ' is staged'

        if message:
            if warnings:
                warn(message)
            continue

        yield output
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

__all__ = ['execute_subprocess', 'status']

if __name__ == '__main__':
    main()
