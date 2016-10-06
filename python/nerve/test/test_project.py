#! /usr/bin/env python
import os
from nerve.core.model import Nerve
# ------------------------------------------------------------------------------

def test_whole_project_cycle():
    config = os.path.join(os.getcwd(), 'python', 'nerve', 'resources', 'nerverc.yml')
    nerve = Nerve(config)

    name = 'nerve-test-repo-2'
    proj = os.path.join(nerve['project-root'], name)

    wd = os.path.exists(proj)
    nerve.delete(name, True, wd)
    print('deleted')
    nerve.create(name)
    print('created')
    nerve.clone(name)
    print('cloned')

    vol001 = os.path.join(proj, 'vol001')
    for i in range(2):
        ver = str(i).zfill(3)
        x = os.path.join(vol001, 'nerve-test-repo-2_desc_' + ver + '.png')
        with open(x, 'w') as f:
            f.write(ver)

    nerve.publish(name)
    print('published')
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
