#! /usr/bin/env python
'''
The utils module contains functions generally usefull to multiple components
within the nerve framework
'''
# ------------------------------------------------------------------------------

from itertools import takewhile
import os
import re
from subprocess import Popen, PIPE, SubprocessError
from warnings import warn
import yaml
from nerve.core.errors import TimeoutError
# ------------------------------------------------------------------------------

def execute_subprocess(command, cwd, error_re='[eE]rror:.*', environment={}, timeout=None):
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

class Name(object):
    def __init__(self, name, project_root=None):
        self.raw = name
        if project_root == None:
            project_root = self.__get_project_root(name)
        self.project_root = project_root
        ftype = self.__get_ftype(name)
        self.ftype = ftype

        attrs = self.__get_attrs(name, ftype)
        for key, val in attrs.items():
            setattr(self, key, val)
    # --------------------------------------------------------------------------

    def __get_project_root(self, fullpath):
        items = fullpath.split(os.sep)
        temp = takewhile(lambda x: not bool(re.search('^[a-z\-]+\d\d\d$', x)), items)
        temp = list(temp)
        if len(temp) != len(items):
            return os.path.join(os.sep, *temp)
        return None

    def __get_attrs(self, raw, ftype):
        root, name = os.path.split(raw)
        name, ext = os.path.splitext(name)
        ext = re.sub('\.', '', ext) if ext != '' else None
        config = True if re.search('nerverc', raw) else False

        template = False
        if re.search('nerverc_temp', raw):
            config = False
            template = True

        items = name.split('_')

        output = dict(
            project_name=None,
            specification=None,
            descriptor=None,
            version=None,
            render_pass=None,
            coordinate=None,
            frame=None,
            meta=None,
            extension=ext,
            config=config,
            template=template
        )
        if ftype != 'unknown':
            output['project_name'] = items[0]

            if ftype == 'template':
                output['specification'] = items[1]
                output['meta'] = False

            elif ftype == 'config':
                if os.path.isfile(raw):
                    with open(raw, 'r') as f:
                        temp = yaml.load(f)
                        if 'specification' in temp:
                            output['specification'] = temp['specification']
                output['meta'] = False

            elif ftype == 'project':
                output['specification'] = items[1]
                output['meta'] = items[2] == 'meta'

            elif ftype == 'asset':
                output.update(self.__get_asset_attrs(items))

        return output
    # --------------------------------------------------------------------------

    def __get_asset_attrs(self, items):
        proj = items[0]
        spec = items[1]
        desc = items[2]
        version = None
        rpass = None
        coord = None
        frame = None
        meta = False

        if len(items) > 3:
            for item in items[3:]:
                if re.search('^v\d+$', item):
                    version = int(re.sub('v', '', item))
                elif re.search('\d\d\d-\d\d\d(-\d\d\d)?', item):
                    coord = tuple(map(int, item.split('-')))
                elif re.search('^\d\d\d\d$', item):
                    frame = int(item)
                elif re.search('^meta$', item):
                    meta = True
                else:
                    rpass = item

        return dict(
            project_name=proj,
            specification=spec,
            descriptor=desc,
            version=version,
            render_pass=rpass,
            coordinate=coord,
            frame=frame,
            meta=meta
        )
    # --------------------------------------------------------------------------

    def __get_ftype(self, raw):
        root, name = os.path.split(raw)
        name, ext = os.path.splitext(name)
        if re.search('nerverc', name):
            if re.search('temp', name):
                return 'template'
            return 'config'

        items = name.split('_')
        if len(items) < 3:
            return 'unknown'

        if re.search('^proj\d+', items[1]):
            return 'project'

        return 'asset'

    @property
    def project_path(self):
        if self.project_root and self.project_name:
            path = os.path.join(self.project_root, self.project_name)
            if os.path.exists(path):
                return path
        return None

    @property
    def specification_path(self):
        if self.project_path and self.specification:
            path = os.path.join(self.project_path, self.specification)
            if os.path.exists(path):
                return path
        return None

    @property
    def fullpath(self):
        def find(item):
            if item:
                output = re.sub(item, '', re.sub('^/', '', self.raw))
                output = os.path.join(item, output)
                if os.path.exists(output):
                    return output
            return None

        raw = self.raw
        if os.path.abspath(raw):
            if os.path.exists(raw):
                return raw

        root = find(self.project_root)
        if root:
            return root

        proj = find(self.project_path)
        if proj:
            return proj

        spec = find(self.specification_path)
        if spec:
            return spec

        return None

    def to_dict(self):
        return {
            'project-root': self.project_root,
            'project-name': self.project_name,
            'project-path': self.project_path,
            'specification-path': self.specification_path,
            'fullpath': self.fullpath,
            'specification': self.specification,
            'descriptor': self.descriptor,
            'version': self.version,
            'render-pass': self.render_pass,
            'coordinate': self.coordinate,
            'frame': self.frame,
            'meta': self.meta,
            'extension': self.extension,
            'config': self.config,
            'template': self.template,
            'ftype': self.ftype,
            'raw': self.raw
        }
# ------------------------------------------------------------------------------

def fetch_project_traits(fullpath):
    '''
    Args:
        fullpath (str): absolute file/directory path

    Returns:
        str: project metadata
    '''
    project = Name(fullpath).project_path
    files = os.listdir(project)
    files = filter(lambda x: re.search('.+_[a-z]+\d\d\d_meta\.yml', x), files)
    files = list(files)
    if len(files) > 0:
        meta = os.path.join(project, files[0])
        with open(meta, 'r') as f:
            meta = yaml.load(f)
            return meta
    return None
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
    'conform_keys',
    'Name',
    'fetch_project_traits'
]

if __name__ == '__main__':
    main()
