#! /usr/bin/env python
import re
from subprocess import Popen, PIPE, STDOUT, SubprocessError, check_output
# ------------------------------------------------------------------------------

def execute_subprocess(command, error_re='Error:.*'):
    output = check_output(command, shell=True, stderr=STDOUT).decode('utf-8')
    error = re.search(error_re, output)
    if error:
        raise SubprocessError('Command: "' + cmd + '" returned "' + error.group(0) + '"')
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
