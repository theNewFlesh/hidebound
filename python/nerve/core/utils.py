#! /usr/bin/env python
import re
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
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

__all__ = ['execute_subprocess']

if __name__ == '__main__':
    main()
