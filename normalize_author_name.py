#!/usr/bin/env python3
"""
Given a name like "H.G. Wells" or "HG Wells" normalize it to a form that's
likely to match ISFDB e.g. "H. G. Wells"

This isn't a proper fuzzy match (not sure what MySQL/MariaDB offers in that
regard) but this might be good enough to catch most cases.
"""

import re
import sys

def normalize_name(author_name):

    # TODO: replace A-Z with a Unicodish value (assuming Python supports them)

    if re.search('^[A-Z]\.[^ ]', author_name): # e.g. "A.Surname", "A.B.Surname"
        # Recurse to cover cases like "A.B.Surname"
        remainder = author_name[2:].strip()
        return author_name[:2] + ' ' + (normalize_name(remainder) or remainder)
    elif re.search('^[A-Z]+ ', author_name): # e.g. "A Surname" or "AB Surname"
        # NB: there are plenty of pseudonyms like "A Person Unnamed" that this
        # will do the wrong thing on, so the caller should always use the original
        # as well as this returned value.

        # Recurse to cover cases like "A B surname"
        remainder = author_name[1:].strip()
        return author_name[0] + '. ' + (normalize_name(remainder) or remainder)

    # TODO: middle initials e.g. "Philip K Dick" -> "Philip K. Dick"

    if ' ' not in author_name:
        return None


    first, remainder = author_name.split(' ', 1)
    if ' ' not in remainder:
        return None
    else:
        ret = normalize_name(remainder)
        if ret:
            return '%s %s' % (first, ret)


    # Deliberately returns None rather than the original author_name to force
    # the caller not to blindly accept this function's return value
    return None




if __name__ == '__main__':
    for name in sys.argv[1:]:
        print('%s -> %s' % (name, normalize_name(name)))



