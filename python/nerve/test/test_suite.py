#! /usr/bin/env python
import os
from subprocess import Popen, PIPE
import time
from nerve.core.model import Nerve
# ------------------------------------------------------------------------------

# def test_whole_project_cycle():
#     config = os.path.join(os.getcwd(), 'python', 'nerve', 'resources', 'nerverc.yml')
#     nerve = Nerve(config)

#     name = 'nerve-test-repo-2'
#     proj = os.path.join(nerve['project-root'], name)

#     wd = os.path.exists(proj)
#     nerve.delete(name, True, wd)
#     print('deleted')
#     nerve.create(name)
#     time.sleep(6)
#     print('created')
#     nerve.clone(name)
#     print('cloned')

#     vol001 = os.path.join(proj, 'vol001')
#     for i in range(2):
#         ver = str(i).zfill(3)
#         x = os.path.join(vol001, 'nerve-test-repo-2_desc_' + ver + '.png')
#         with open(x, 'w') as f:
#             f.write(ver)

#     nerve.publish(name)
#     print('published')

def test_publish():
    config = '/Users/alex/Documents/projects/nerve/python/nerve/resources/nerverc.yml'
    nerve = Nerve(config)
    wd = os.path.join(nerve['project-root'], nerve['project']['project-name'])
    cmd = [
        'cd ' + wd + ' /vol001/',
        'mkdir nerve-test-repo-3_vol001_desc_v001_-_-_-',
        'cd nerve-test-repo-3_vol001_desc_v001_-_-_-',
        'echo v001 0000 >> nerve-test-repo-3_vol001_desc_v001_-_-_0000.png',
        'echo v001 0001 >> nerve-test-repo-3_vol001_desc_v001_-_-_0001.png',
        'echo v001 0002 >> nerve-test-repo-3_vol001_desc_v001_-_-_0002.png',
        'cd ../../maya001',
        'echo vasc vasc v001 >> nerve-test-repo-3_maya001_vasculature.mb',
        'echo vasc kidney v001 >> nerve-test-repo-3_maya001_kidney.mb',
        'git add --all',
        'git commit -m "test publish commit"'
    ]
    cmd = '; '.join(cmd)
    Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, cwd=wd)

    nerve.publish(
        notes='create vol001_v001; if you can read this, it probably worked',
        verbosity=2
    )
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

# __all__ = []

if __name__ == '__main__':
    main()
