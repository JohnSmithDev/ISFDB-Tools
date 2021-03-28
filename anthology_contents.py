#!/usr/bin/env python3
"""
Dump out the contents of an anthology or collection.

(Or possibly omnibus/chapbook/magazine as well, but I'm not planning on testing
those right now)

Usage:

  ./anthology_contents.py 2842014

Where the number is the relevant title ID

"""

from collections import defaultdict, Counter, namedtuple
# from functools import reduce, lru_cache
from itertools import chain # aka flatten
import logging
import pdb
import sys


from sqlalchemy.sql import text

from common import (get_connection, parse_args, AmbiguousArgumentsError)

RELEVANT_CONTENT_TYPES = ['SHORTFICTION'] # Maybe ESSAY as well?

TitleStuff = namedtuple('TitleStuff', 'id, title, year, '
                        'author_id, author_canonical, author_legalname, author_lastname')
PubStuff = namedtuple('PubStuff', 'page, pub_id, pub_title')


def get_pubs_for_title(conn, title_id):
    """
    Return a list of all the pub IDs for a title ID
    """
    query = text("""
    SELECT pub_id
    FROM pub_content
    WHERE title_id = :title_id;
    """)
    rows = conn.execute(query, {'title_id': title_id})
    return [z.pub_id for z in rows]


def get_contents_of_title(conn, title_id):
    """
    Return a list [*] of contents of a title, across all of its publications.
    This is likely to return duplicate titles, for each publication that contains
    that story (or essay, etc).  Feed the output of this function to
    postprocess_contents() to merge rows appropriately.

    [* or whatever iterable SQLAlchemy returns]
    """

    pub_ids = get_pubs_for_title(conn, title_id)
    # print(pub_ids)

    # pubc_page is a string, so ordering isn't especially useful
    query = text("""
    SELECT ct.title_id, ct.title_title, YEAR(ct.title_copyright) year, ct.title_ttype,
       ca.author_id, a.author_canonical, a.author_legalname, a.author_lastname,
       pc.pubc_page, p.pub_id, p.pub_title, p.pub_ctype
    FROM pubs p
    LEFT OUTER JOIN pub_content pc ON pc.pub_id = p.pub_id
    LEFT OUTER JOIN titles ct ON pc.title_id = ct.title_id
    LEFT OUTER JOIN canonical_author ca ON ca.title_id = ct.title_id
    LEFT OUTER JOIN authors a ON a.author_id = ca.author_id
    WHERE p.pub_id in :pub_ids
      AND ct.title_ttype IN :relevant_content_types
    ORDER BY pc.pubc_page, p.pub_id
    ;""")
    rows = conn.execute(query, {'pub_ids': pub_ids,
                                'relevant_content_types': RELEVANT_CONTENT_TYPES})
    return rows



def postprocess_contents(content_rows):
    """
    Not all pubs for a given title will have the same contents.  (And many pubs
    will not have any contents defined, although there's nothing we can do about
    that here really.)  Example title ID: 30301

    As such, turn the individual rows - which may well have dupes or inconsistencies
    across pubs) into a structure mapping title stuff to the pubs it appears in.
    """
    ret = defaultdict(set)

    for row in content_rows:
        t_key = TitleStuff(row.title_id, row.title_title, row.year,
                           row.author_id, row.author_canonical,
                           row.author_legalname, row.author_lastname)
        pub_bits = PubStuff(row.pubc_page, row.pub_id, row.pub_title)
        ret[t_key].add(pub_bits)
    return ret


def output_contents(contents, output_function=print):
    # The logic for determining titles not appearing in all pubs should probably
    # be factored out, but I wonder if it could/should be made more generic
    # first? e.g. some sort of reverse map of pubs to stories?
    raw_known_pubs = []
    for pub_details in contents.values():
        raw_known_pubs.append([z.pub_id for z in pub_details])
    known_pubs = set(chain(*raw_known_pubs)) # flatten and remove dupes
    # output_function(known_pubs)
    for title_stuff, pub_stuff in contents.items():
        if len(pub_stuff) < len(known_pubs):
            warning = ' - Does not appear in all publications of this title'
        else:
            warning = ''
        output_function(f'* {title_stuff.author_canonical} - '
                        f'"{title_stuff.title}" [{title_stuff.year}]{warning}')


def output_title(conn, title_id, output_function=print):
    contents = get_contents_of_title(conn, title_id) # e.g. 34696
    processed_data = postprocess_contents(contents)
    output_contents(processed_data, output_function)


if __name__ == '__main__':
    conn = get_connection()

    title_id = int(sys.argv[1])
    output_title(conn, title_id)
