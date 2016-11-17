#! /usr/bin/env python
'''
The Name class return properties of file and directory names

Platforrm:
    Unix

Author:
    Alex Braun <alexander.g.braun@gmail.com> <http://www.alexgbraun.com>
'''
# ------------------------------------------------------------------------------

import os
import re
# ------------------------------------------------------------------------------

class Name(object):
    def __init__(self, name, project_root):
        self.raw = name
        self.project_root = project_root
        ftype = self.__get_ftype(name)
        self.ftype = ftype

        attrs = self.__get_attrs(name, ftype)
        for key, val in attrs.items():
            setattr(self, key, val)
    # --------------------------------------------------------------------------

    def __get_attrs(self, raw, ftype):
        root, name = os.path.split(raw)
        name, ext = os.path.splitext(name)
        items = name.split('_')

        output = dict(
            project_name=None,
            specification=None,
            descriptor=None,
            version=None,
            render_pass=None,
            coordinates=None,
            frame=None,
            meta=None
        )
        ext = ext if ext != '' else None
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
        meta = None

        if len(items) > 3:
            items = items[3:]

        for item in items:
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
            coordinates=coord,
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
        if self.project_name:
            path = os.path.join(self.project_root, self.project_name)
            if os.path.exists(path):
                return path
        return None

    @property
    def specification_path(self):
        if self.project_path:
            if self.specification:
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
        return dict(
            project_name=self.project_name,
            project_path=self.project_path,
            specification_path=self.specification_path,
            fullpath=self.fullpath,
            project_root=self.project_root,
            specification=self.specification,
            descriptor=self.descriptor,
            version=self.version,
            render_pass=self.render_pass,
            coordinates=self.coordinates,
            frame=self.frame,
            meta=self.meta,
            ftype=self.ftype,
            raw=self.raw
        )
