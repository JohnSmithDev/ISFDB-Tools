#!/usr/bin/env python3
"""
Return a list of authors for a title_id.  Note that this only shows the editor(s)
for anthologies, not the contributors.

This is unlikely to be useful as a regular standalone script - it's primarily
for me to quickly check data.
"""

import pdb
import sys

from sqlalchemy.sql import text

from common import get_connection

from title_related import get_authors_for_title

if __name__ == '__main__':
    conn = get_connection()
    for i, tidstr in enumerate(sys.argv[1:]):
        if i > 0:
            print()
        authors = get_authors_for_title(conn, int(tidstr))
        for author in authors:
            print('%s (author_id=%d)' % (author.name, author.id))


