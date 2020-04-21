#! /usr/bin/env python

import os

def restyle_css(css):
    '''
    restyle theme.css
    '''
    custom = '''
.docutils dd ul.first.last.simple {
    font-size: 90% !important;
}
.docutils dt {
    background: #FDFDFD !important;
    border-left: 0px !important;
}
'''
    text = []
    with open(css, 'r') as f:
        text = f.readlines()

    with open(css, 'w') as f:
        f.write(text[0][:-4])
        f.write(custom)
        f.write('/*!\n')
        for line in text[1:]:
            f.write(line)

def main():
    css = os.getcwd()
    css += '/_build/html/_static/css/theme.css'
    restyle_css(css)

if __name__ == '__main__':
    main()
