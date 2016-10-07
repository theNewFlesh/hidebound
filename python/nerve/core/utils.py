#! /usr/bin/env python
import os
import re
from warnings import warn
from subprocess import Popen, PIPE, STDOUT, SubprocessError
# ------------------------------------------------------------------------------

def get_asset_name_traits(fullpath):
    ext = None
    name = os.path.split(fullpath)[-1]

    # skip hidden files
    if name[0] == '.':
        return {}

    if os.path.isfile(fullpath):
        name, ext = os.path.splitext(name)
    traits = name.split('_')

    output = dict(
        asset_name=name,
        project_name=traits[0],
        specification=traits[1],
        descriptor=traits[2],
        version=traits[3],
    )

    if ext:
        output['extension'] = ext

    if len(traits) > 4:
        traits = re.split(name, 'v\d\d\d')[-1].split('_')
        for trait in traits:

            if re.search('\d\d\d-\d\d\d-\d\d\d'):
                x,y,z = [int(x) for x in trait.split('-')]
                output['coordinates'] = dict(x=x, y=y, z=z)
            elif re.search('\d\d\d\d', trait):
                output['frame'] = int(trait)
            else:
                output['render_pass'] = trait

    return output
# ------------------------------------------------------------------------------

def execute_subprocess(command, error_re='Error:.*'):
    '''
    Executes a given command as a subprocess and scrubs the output for errors

    Args:
        command (str): shell command to be run
        error_re (str, optional): regex used for capturing errors

    Returns:
        list: lines of output

    Raises:
        SubprocessError: stdout error as message
    '''
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

def status(self, command, include=[], exclude=[], states=[], staged=None, warnings=False):
    '''
    Convenience function for running a git or git lfs status command and returning nice output

    Args:
        command (str): command to be run. [git or git lfs] status --porcelain
        include (list, optional): list of regex patterns used to include files. Default: []
        exclude (list, optional): list of regex patterns used to exclude files. Default: []
        states (list, optional): file states to be shown in output. Default: all states
            options include: added, copied, deleted, modified, renamed, updated, untracked
        staged (bool, optional): include only files which are staged or unstaged. Default: both
        warnings (bool, optional): display warnings

    Returns:
        list: list of dicts, each one representing a file
    '''
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

    if include:
        include = re.compile('|'.join(include))
    if exclude:
        exclude = re.compile('|'.join(exclude))
    # ----------------------------------------------------------------------

    # for item in self._repo.index.diff('HEAD', R=True):
    #     output = dict(
    #         fullpath=item.a_path, # is this always correct?
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
        fullpath = item[3:].split(' ')[0]
        output['fullpath'] = fullpath
        # ------------------------------------------------------------------

        message = []
        _states = states[0]
        if len(states) > 1:
            _states = ', '.join(states[:-1]) + ' or ' + states[-1]

        if include:
            found = include.search(fullpath)
            if not found:
                message.append(fullpath + ' is excluded')
        if exclude:
            found = exclude.search(fullpath)
            if found:
                message.append(fullpath + ' is excluded')
        if states:
            if output['state'] not in states:
                message.append(fullpath + ' is not ' + _states)
        if staged != None:
            if output['staged'] != staged:
                if staged:
                    message.append(fullpath + ' is unstaged')
                else:
                    message.append(fullpath + ' is staged')

        if len(message) > 0:
            if warnings is True:
                warn('. '.join(message))
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

__all__ = [
    'get_asset_name_traits',
    'execute_subprocess',
    'status'
]

if __name__ == '__main__':
    main()
