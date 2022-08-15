#!/usr/bin/env python3
"""
Tools/functions to dig out the publication history of a title.

See also the older publication_history.py script - that is focussed on "books",
whereas this is aimed at short fiction titles (initially at least)

"""

import pdb
import sys

from sqlalchemy.sql import text

from common import get_connection

class UnexpectedDataError(Exception):
    pass
class NoPublicationsFoundError(Exception):
    pass

def get_raw_publications_for_title_ids(conn, title_ids):
    """
    Base function that doesn't do anything clever with magazines
    """
    query = text("""SELECT p.pub_id, pub_title, CAST(pub_year AS CHAR) pub_date,
    pub_ptype, pub_ctype, pub_price, pubc_page,
    p.publisher_id, pb.publisher_name
    FROM pubs p
    LEFT OUTER JOIN publishers pb ON p.publisher_id = pb.publisher_id
    LEFT OUTER JOIN pub_content pc ON pc.pub_id = p.pub_id
    WHERE pc.title_id IN :title_ids
    ORDER by pub_year, p.pub_id, pubc_page, pub_title;""")

    results = conn.execute(query, {'title_ids': title_ids}).fetchall()
    return results


def get_title_editor_for_pub_id(conn, pub_id):
    # I think this needs to be made cleverer w.r.t. variant titles
    # (Some tor.com with author/editor variant name IIRC)
    query = text("""SELECT t.title_id, t.title_title,  t.series_id, s.series_title
FROM pub_content pc
LEFT OUTER JOIN titles t ON pc.title_id = t.title_id
LEFT OUTER JOIN series s ON t.series_id = s.series_id
WHERE pc.pub_id = :pub_id AND t.title_ttype = 'EDITOR';""")
    results = conn.execute(query, {'pub_id': pub_id}).fetchall()
    if len(results) != 1:
        raise UnexpectedDataError(f'Found %d EDITOR titles for pub_id %d' %
                                  (len(results), pub_id))
    return results[0]


def get_publications_for_title_ids(conn, title_ids):
    """
    Given a list/iterable of title_ids, return a list of PubDetails

    Intended use case is that title_ids are author/title variants of the same
    fundamental story (or in theory non-fiction, art etc), but probably you
    could feed in any arbitrary IDs.
    """
    raw_results = get_raw_publications_for_title_ids(conn, title_ids)

    results = []
    for r in raw_results:
        new_r = dict(r)
        if r.pub_ctype == 'MAGAZINE':
            # new_r.append(get_title_editor_for_pub_id(conn, r.pub_id))
            mag_stuff = get_title_editor_for_pub_id(conn, r.pub_id)
            new_r['publisher_id'] = None
            new_r['publisher_name'] = mag_stuff.series_title or mag_stuff.title_title
        elif r.pub_ctype in ('COLLECTION', 'ANTHOLOGY'):
            new_r['publisher_id'] = None
            new_r['publisher_name'] = r.pub_title

        results.append(new_r)

    return results


def extract_earliest_pub(pub_stuff):
    sorted_clean_data = sorted([z for z in pub_stuff if z['pub_date'] != '0000-00-00'],
                               key=lambda z: z['pub_date'])
    if sorted_clean_data:
        return sorted_clean_data[0]
    else:
        # Shouldn't ever happen, but make a best effort...
        return sorted(pub_stuff, key=lambda z: z['pub_date'])[0]


def get_earliest_pub(conn, title_ids):
    raw_results = get_publications_for_title_ids(conn, title_ids)
    if not raw_results:
        raise NoPublicationsFoundError('No publications for for title_ids %s' %
                                       (title_ids))
    return extract_earliest_pub(raw_results)

if __name__ == '__main__':
    # This is just for quick hacks/tests, not intended for "real" use
    conn = get_connection()

    title_ids = [int(z) for z in sys.argv[1:]]
    publications = get_publications_for_title_ids(conn, title_ids)
    for p in publications:
        print(p)
    print()
    print(extract_earliest_pub(publications))

