#! /usr/bin/env python
'''
The utils module contains functions generally usefull to multiple components
within the nerve framework
'''
# ------------------------------------------------------------------------------

import os
import re
from warnings import warn
from subprocess import Popen, PIPE, SubprocessError
from nerve.core.errors import TimeoutError
# ------------------------------------------------------------------------------

def execute_subprocess(command, cwd, error_re='[eE]rror:.*', environment={}, timeout=100):
    '''
    Executes a given command as a subprocess and scrubs the output for errors

    Args:
        command (str): shell command to be run
        cwd (str): current working directory
        error_re (str, optional): regex used for capturing errors

    Returns:
        list: lines of output

    Raises:
        SubprocessError: stdout error as message
    '''
    if environment != {}:
        temp = ['{}="{}"'.format(k,v) for k,v in environment.items()]
        temp.append(command)
        command = ' '.join(temp)

    output = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
    output.wait(timeout=timeout)
    stderr = output.stderr.read().decode('utf-8')
    output = output.stdout.readlines()
    output = [x.decode('utf-8').strip('\n') for x in output]

    err = '\n'.join(output)
    err += stderr
    error = re.search(error_re, err)
    if error:
        message = 'Command: "' + command
        message += '" returned "' + error.group(0) + '"'
        raise SubprocessError(message)

    return output

def get_status(command, working_dir, include=[], exclude=[], states=[], staged=None, warnings=False):
    '''
    Convenience function for running a git or git lfs status command and returning nice output

    Args:
        command (str): command to be run. [git or git lfs] status --porcelain
        include (list, optional): list of regex patterns used to include files. Default: []
        exclude (list, optional): list of regex patterns used to exclude files. Default: []
        states (list, optional): file states to be shown in output. Default: all states
            Options: added, copied, deleted, modified, renamed, updated, untracked
        staged (bool, optional): include only files which are staged or unstaged. Default: both
        warnings (bool, optional): display warnings

    Yields:
        dict: a single file
    '''
    os.chdir(working_dir)
    status_ = execute_subprocess(command, working_dir)
    lut = {
        'A': 'added',
        'C': 'copied',
        'D': 'deleted',
        'M': 'modified',
        'R': 'renamed',
        'U': 'updated',
        '?': 'untracked'
    }

    if include:
        include = re.compile('|'.join(include))
    if exclude:
        exclude = re.compile('|'.join(exclude))
    # ----------------------------------------------------------------------

    for item in status_:
        output = {}
        output['staged'] = False
        if item[0] != ' ':
            output['staged'] = True
            output['state'] = lut[item[0]]
        else:
            output['state'] = lut[item[1]]
        path = item[3:].split(' ')[0]
        output['path'] = path
        fullpath = os.path.join(working_dir, path)
        fullpath = re.sub(os.sep + '$', '', fullpath)
        output['fullpath'] = fullpath
        # ------------------------------------------------------------------

        message = []

        if include:
            found = include.search(path)
            if not found:
                message.append(path + ' is excluded')
        if exclude:
            found = exclude.search(path)
            if found:
                message.append(path + ' is excluded')
        if states:
            if output['state'] not in states:
                message.append(path + ' is not ' + ', '.join(states))
        if staged != None:
            if output['staged'] != staged:
                if staged:
                    message.append(path + ' is unstaged')
                else:
                    message.append(path + ' is staged')

        if message:
            if warnings is True:
                warn('. '.join(message))
            continue

        yield output

def is_dictlike(item):
    '''Determine if an item id dictlike'''
    return item.__class__.__name__ in ['dict', 'OrderedDict']

def deep_update(original, update):
    '''
    Recursively updates an original dictionary with an update dictionary

    Args:
        original (dict): original dictionary
        update (dict): dictionary to be merged

    Returns:
        dict: new updated dictionary
    '''
    for key, value in original.items():
        if not key in update:
            update[key] = value
        elif isinstance(value, dict):
            deep_update(value, update[key])
    return update

def conform_keys(data, source='_', target='-', skip=[]):
    '''
    Recursively renames a dictionary's keys

    Args:
        data (dict): dictionary to be conformed
        source (str, optional): regex pattern to match in keys. Default: '_'
        target (str, optional): replacement string. Default: '-'
        skip (list, optional): keys to skip. Default: []

    Returns:
        dict: conformed dictionary
    '''
    def _conform(data, store):
        if not is_dictlike(data):
            return data
        for key, val in data.items():
            if key in skip:
                store[key] = val
            elif is_dictlike(val):
                store[re.sub(source, target, key)] = _conform(val, {})
            else:
                store[re.sub(source, target, key)] = val
        return store
    return _conform(data, {})
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

__all__ = [
    'execute_subprocess',
    'get_status',
    'is_dictlike',
    'deep_update',
    'conform_keys'
]

if __name__ == '__main__':
    main()
