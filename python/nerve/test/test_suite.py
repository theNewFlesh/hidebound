#! /usr/bin/env python
import os
import re
from subprocess import Popen, PIPE
import time
# from nerve.core.model import Nerve
from nerve.core.git_lfs import GitLFS
from nerve.core.git import Git
from nerve.core.utils import execute_subprocess
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
    cwd = os.path.join(nerve['project-root'], nerve['project']['project-name'])
    command = [
        'cd ' + cwd,
        'mkdir vol001/ntr002_vol001_desc_v001_-_-_-',
        'echo v001 0000 > vol001/ntr002_vol001_desc_v001_-_-_-/ntr002_vol001_desc_v001_-_-_0000.png',
        'echo v001 0001 > vol001/ntr002_vol001_desc_v001_-_-_-/ntr002_vol001_desc_v001_-_-_0001.png',
        'echo v001 0002 > vol001/ntr002_vol001_desc_v001_-_-_-/ntr002_vol001_desc_v001_-_-_0002.png',
        'echo vasc v001 > maya001/ntr002_maya001_vasc_v001.mb',
        'echo kidney v001 > maya001/ntr002_maya001_kdny_v001.mb',
        'git add --all',
        'git commit -m "test publish commit"'
    ]
    command = '; '.join(command)
    Popen(command, shell=True, stdout=PIPE, stderr=PIPE, cwd=cwd)

    info = nerve._get_info(None, None, {})
    environment = info.env
    local = Git(cwd, branch=info.branch)
    commit = local.references(branches=info.branch, reftypes='local')
    commit = list(commit)[0]['commit']

    origin = 'origin'
    # origin = 'http://alex:nerve@localhost:8080'
    command = 'GIT_TRACE=1 git push {remote} {branch}'.format(remote=origin, branch=info.branch)
    stdout = execute_subprocess(command, cwd, environment=environment)
    print(stdout, '\n')

    # if environment != {}:
    #     temp = ['{}={}'.format(k,v) for k,v in environment.items()]
    #     temp.append(command)
    #     command = ' '.join(temp)

    # output = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, cwd=cwd)
    # output.wait()
    # print(output.stdout.read())
    # print(output.stderr.read())
    # print(output.returncode)

    # nerve.publish(
    #     notes='create vol001_v001; if you can read this, it probably worked',
    #     verbosity=2vim
    # )
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
