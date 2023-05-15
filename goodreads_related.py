#!/usr/bin/env python3
"""
Goodreads ID related functions

"""

from collections import namedtuple

from sqlalchemy.sql import text

from find_book import BookNotFoundError
from common import get_connection

# These are defined in identifier_types; possible TODO replace this hardcoding
# with a join to that table in the SQL query
GOODREADS_ID_ID = 8

PubAndTitleStuff = namedtuple('PubAndTitleStuff', 'pub_id, pub_title, ' + \
                              'ptype, ctype, title_id, title_title, ttype')

def get_ids_from_goodreads_id(conn, gr_id):
    query = text("""SELECT p.pub_id, pub_title,
    p.pub_ptype ptype, p.pub_ctype ctype,
    t.title_id, t.title_title, t.title_ttype ttype
    FROM pubs p
    LEFT OUTER JOIN identifiers i ON i.pub_id = p.pub_id
    LEFT OUTER JOIN pub_content pc ON pc.pub_id = p.pub_id
    LEFT OUTER JOIN titles t ON t.title_id = pc.title_id
    WHERE i.identifier_value = :gr_id
    AND i.identifier_type_id = :gr_id_id
    AND p.pub_ctype = t.title_ttype
    ORDER BY p.pub_id;""")

    results = conn.execute(query, {'gr_id': str(gr_id),
                                   'gr_id_id': GOODREADS_ID_ID})
    ret = []
    for row in results:
        ret.append(row._mapping)
    if not ret:
        raise BookNotFoundError(f'Goodreads ID {gr_id} is not known to ISFDB')
    return ret

if __name__ == '__main__':
    # This is just for quick hacks/tests, not intended for "real" use
    conn = get_connection()

    import sys
    gr_id = int(sys.argv[1])
    results = get_ids_from_goodreads_id(conn, gr_id)
    for detail in results:
        print(detail)
