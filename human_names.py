#!/usr/bin/env python3
"""
A simple module to utilize the data in the human-names repo at
https://github.com/AlessandroMinoccheri/human-names

Set the HUMAN_NAMES_REPO_DIR environment variable to the location of your
checkout of that repo.  Optionally set HUMAN_NAMES_LANGUAGES to a comma
separated list of languages if you don't want the default of just "en".

NB: The names in that repo are debatably accurate - e.g. "Pat" is listed as
a male-only name, which is clearly not the case.

"""

from collections import defaultdict
import json
import logging
import os
import pdb
import sys

LANGUAGES = os.environ.get('HUMAN_NAMES_LANGUAGES') or ('en',)
gendered_names = defaultdict(set)

hnr_base_dir = os.environ.get('HUMAN_NAMES_REPO_DIR')
if not hnr_base_dir:
    hnr_base_dir = os.path.join(os.path.dirname(__file__), 'human-names')
hnr_data_dir = os.path.join(hnr_base_dir, 'data')
if not os.path.exists(hnr_data_dir):
    raise FileNotFoundError('No human-names data directory found, '
                            'try setting HUMAN_NAMES_REPO_DIR and/or '
                            'checking out the human-names repo/submodule')

for gender in ('female', 'male'):
    for lang in LANGUAGES:
        fn = os.path.join(hnr_data_dir,
                          '%s-human-names-%s.json' % (gender, lang))
        with open(fn) as inputstream:
            name_list = json.load(inputstream)
            gendered_names[gender].update(name_list)

gendered_names['male-only'] = gendered_names['male'].difference(gendered_names['female'])
gendered_names['female-only'] = gendered_names['female'].difference(gendered_names['male'])


def derive_gender_from_name(name, strict=True):
    """
    Returns 'M' or 'F', or None if the name is not known, or the name appears
    in both male and female lists and strict=True.
    (Behaviour is currently somewhat undefined if strict=False and the name
    appears in both lists - either 'M' or 'F' could be returned in such as case.)
    """
    if strict:
        mappings = {'M': 'male-only', 'F': 'female-only'}
    else:
        mappings = {'M': 'male', 'F': 'female'}
    for gender_char, gender_key in mappings.items():
        if name in gendered_names[gender_key]:
            return gender_char
    else:
        return None

if __name__ == '__main__':
    for name in sys.argv[1:]:
        print('%s : %s' % (name, derive_gender_from_name(name)))

