#!/usr/bin/env python
"""
Quick and dirty script to increment the most minor number in the version field
of a manifest.json file
"""

try:
    import simplejson as json
except ModuleNotFoundError:
    # Assume it's because Python3 calls it json by default
    import json

FILE = 'manifest.json'


def bump_version_number(v):
    vbits = v.split('.')
    inced = str(int(vbits[-1]) + 1)
    vbits[-1] = inced
    v = '.'.join(vbits)
    return v

def main(filename):
    with open(filename) as finput:
        cfg = json.load(finput)

    cfg['version'] = bump_version_number(cfg['version'])

    with open(filename, 'w') as foutput:
        foutput.write(json.dumps(cfg, indent='  '))

    print('Bumped up to %s' % (cfg['version']))

if __name__ == '__main__':
    main(FILE)
