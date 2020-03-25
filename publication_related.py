#!/usr/bin/env python3
"""
Publication related functions.

Some of these may well overlap with the code in publication_history.py
"""

from collections import namedtuple

from sqlalchemy.sql import text

from country_related import derive_country_from_price


PubInfo = namedtuple('PubInfo',
                     'pub_id, fmt, isbn, identifier_type, identifier, publisher, price, country')

def find_pubs_for_title_ids(conn, title_ids):
    """
    Return a list of PubInfo tuples for any publication records for the titles
    in title_ids.

    Note: this could return duplicates for pub_id/pub_ptype/pub_isbn if there
    are multiple other IDs associated with this publication

    TODO: parameterize the relevant identifier types

    This is similar to  publication_history._get_publications in isfdb_tools,
    but I'm reluctant to refactor/merge them due to the different JOINs involved,
    and potential performance issues grabbing stuff you might not need.
    """
    query = text("""SELECT p.pub_id, pub_ptype,
                    pub_isbn, identifier_type_name, identifier_value,
                    publisher_name, pub_price
    FROM pubs p
    LEFT OUTER JOIN pub_content pc ON p.pub_id = pc.pub_id
    LEFT OUTER JOIN identifiers i  ON i.pub_id = p.pub_id
    LEFT OUTER JOIN identifier_types it ON i.identifier_type_id = it.identifier_type_id
    LEFT OUTER JOIN publishers ON publishers.publisher_id = p.publisher_id
    WHERE pc.title_id in :title_ids;""")
    results = conn.execute(query, {'title_ids': title_ids}).fetchall()

    return {PubInfo(z['pub_id'], z['pub_ptype'],
                    z['pub_isbn'], z['identifier_type_name'], z['identifier_value'],
                    z['publisher_name'],
                    z['pub_price'], derive_country_from_price(z['pub_price']))
            for z in results}
