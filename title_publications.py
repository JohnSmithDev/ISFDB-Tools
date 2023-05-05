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
from country_related import derive_country_from_price


class UnexpectedDataError(Exception):
    pass
class NoPublicationsFoundError(Exception):
    pass

def get_raw_publications_for_title_ids(conn, title_ids):
    """
    Base function that doesn't do anything clever with magazines (in terms of turning a
    particular issue into the overall EDITOR/series.
    """
    query = text("""SELECT p.pub_id, pub_title, CAST(pub_year AS CHAR) pub_date,
    pub_ptype, pub_ctype, pub_price, pubc_page,
    p.publisher_id, pb.publisher_name,
    p.pub_series_id, pub_series_name
    FROM pubs p
    LEFT OUTER JOIN publishers pb ON p.publisher_id = pb.publisher_id
    LEFT OUTER JOIN pub_content pc ON pc.pub_id = p.pub_id
    LEFT OUTER JOIN pub_series ps ON ps.pub_series_id = p.pub_series_id
    WHERE pc.title_id IN :title_ids
    ORDER by pub_year, p.pub_id, pubc_page, pub_title;""")

    results = conn.execute(query, {'title_ids': title_ids}).fetchall()
    return results


def get_title_editor_for_title_id(conn, title_id):
    # This may help with the odd case in the function below - pass the title_parent into this
    query = text("""SELECT t.title_id, t.title_title, t.title_parent,
    t.series_id, s.series_title
FROM titles t
LEFT OUTER JOIN series s ON t.series_id = s.series_id
WHERE t.title_id = :title_id AND t.title_ttype = 'EDITOR';""")
    results = conn.execute(query, {'title_id': title_id}).fetchall()
    if len(results) != 1:
        raise UnexpectedDataError(f'Found %d EDITOR titles for title_id %d' %
                                  (len(results), title_id))
    return results[0]

def get_title_editor_for_pub_id(conn, pub_id):
    # I think this needs to be made cleverer w.r.t. variant titles
    # (Some tor.com with author/editor variant name IIRC
    # F&SF title_id 2108266 vs title_id 2108298 is similar I think?

    query = text("""SELECT t.title_id, t.title_title, t.title_parent,
    t.series_id, s.series_title
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
    ... What are "PubDetails", they aren't referenced anywhere in the code except here ...

    This returns a list of dicts (for now)

    Intended use case is that title_ids are author/title variants of the same
    fundamental story (or in theory non-fiction, art etc), but probably you
    could feed in any arbitrary IDs.
    """
    raw_results = get_raw_publications_for_title_ids(conn, title_ids)

    results = []
    for r in raw_results:
        new_r = dict(r._mapping)
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


def extract_earliest_pub(pub_stuff, only_from_country=None):
    def has_known_date(pub_info):
        return pub_info['pub_date'] not in ('0000-00-00', '8888-00-00')

    def has_known_date_and_from_specific_country(pub_info):
        return has_known_date(pub_info) and \
            derive_country_from_price(pub_info['pub_price']) == only_from_country

    if only_from_country:
        filter_func = has_known_date_and_from_specific_country
    else:
        filter_func = has_known_date


    sorted_clean_data = sorted([z for z in pub_stuff if filter_func(z)],
                               key=lambda z: z['pub_date'])
    if sorted_clean_data:
        return sorted_clean_data[0]
    else:
        if only_from_country:
            # Try again with any country
            return extract_earliest_pub(pub_stuff)
        else:
            # Shouldn't ever happen, but make a best effort...
            return sorted(pub_stuff, key=lambda z: z['pub_date'])[0]


def get_earliest_pub(conn, title_ids, only_from_country=None):
    """
    Return a dict with various pub properties for the earliest publication of any of the given
    title_ids.  (It is assumed that the caller has done any lookups on the title_id to find
    all the relevant variants it might have been published as)
    """
    raw_results = get_publications_for_title_ids(conn, title_ids)
    if not raw_results:
        raise NoPublicationsFoundError('No publications for for title_ids %s' %
                                       (title_ids))
    return extract_earliest_pub(raw_results, only_from_country)

if __name__ == '__main__':
    # This is just for quick hacks/tests, not intended for "real" use
    conn = get_connection()

    title_ids = [int(z) for z in sys.argv[1:]]
    publications = get_publications_for_title_ids(conn, title_ids)
    for p in publications:
        print(p)
    print()
    print(extract_earliest_pub(publications))

