#!/usr/bin/env python3
"""
Get the tag IDs and names associated with a title (ID).

This will probably more useful as a library function than as a standalone
script.

"""

import pdb
import sys

from sqlalchemy.sql import text

from common import (get_connection, parse_args, AmbiguousArgumentsError)

def get_title_tags(conn, title_id):
    """
    Return an object containing an iterable (tag_id, tag_name, frequency)
    row/tuple thingies for a title.
    """
    query = text("""SELECT t.tag_id, tag_name, c frequency
      FROM (
        SELECT tag_id, COUNT(1) c
        FROM tag_mapping tm
        WHERE title_id = :title_id
        GROUP BY tag_id
      ) tags_used
      LEFT OUTER JOIN tags t ON t.tag_id = tags_used.tag_id
      ORDER BY c desc;""")
    rows = conn.execute(query, {'title_id': title_id})
    return rows


if __name__ == '__main__':
    conn = get_connection()

    for i, title_arg in enumerate(sys.argv[1:]):
        title_id = int(title_arg)
        if i > 0:
            print('')
        if len(sys.argv) > 1:
            print('= %d =' % title_id)
        for row in get_title_tags(conn, title_id):
            # There are lots of tags >40 chars, but most of them are stuff like
            # "Foo award winner" that arguably/IMHO should be modelled
            # differently
            print('* %5d : %-40s %d occurrences' % (row.tag_id, row.tag_name,
                                                    row.frequency))
