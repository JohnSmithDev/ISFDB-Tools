#!/usr/bin/env python
"""
Show all the different formats and countries a book was published in.

(The script name is a bit of misnomer.  TODO: rename it.)

TODO: Clean up this right mess, in large part due to confusiom over parent and
child IDs.


"""

from argparse import ArgumentParser
from datetime import date
from collections import namedtuple, defaultdict
import logging
import pdb
import re
import sys

from sqlalchemy.sql import text

from country_related import (derive_country_from_price, get_country)
from common import (get_connection, parse_args,
                    get_filters_and_params_from_args,
                    AmbiguousArgumentsError)
from isfdb_utils import convert_dateish_to_date
from author_aliases import get_author_aliases
from title_related import get_title_ids

AuthorBook = namedtuple('AuthorBook', 'author, book')

UNKNOWN_COUNTRY = 'XX'

def get_publications(conn, title_ids, verbose=False):
    """
    This takes a list of title_ids because it seems we have to use both the
    child and the parent to be sure of finding matching pubs
    """
    query = text("""SELECT pub_ptype format,
                           CAST(pub_year AS CHAR) dateish,
                           pub_isbn isbn,
                           pub_price price,
                           pc.title_id title_id
      FROM pub_content pc
      LEFT OUTER JOIN pubs p ON p.pub_id = pc.pub_id
      WHERE pc.title_id IN :title_ids
        ORDER BY p.pub_year""")
    results = conn.execute(query, title_ids=title_ids)
    # pdb.set_trace()
    rows = list(results)
    ret = defaultdict(list)
    for row in rows:
        # print(row['pub_price'])
        ref = 'title_id=%d,ISBN=%s' % (row['title_id'], row['isbn'])
        country = derive_country_from_price(row['price'], ref=ref)
        if not country:
            if verbose:
                logging.warning('Unable to derive country fom price "%s"' %
                                row['price'])
            country = UNKNOWN_COUNTRY
        dt = convert_dateish_to_date(row['dateish'])
        ret[country].append((row['format'],
                             dt or None,
                             row['isbn'] or None))
    return ret

def render_details(pubs, output_function=print):
    # print(pubs)
    for country, details in pubs.items():
        output_function(country)
        for detail in details:
            output_function('%10s published %-12s (ISBN:%s)' % (detail))


if __name__ == '__main__':
    args = parse_args(sys.argv[1:],
                      description='List publication countries and dates for a book',
                      supported_args='antv')

    conn = get_connection()
    FIRST_ATTEMPT = """
    title_id_dict = get_title_id(conn, args)
    if len(title_id_dict) > 1:
        raise AmbiguousArgumentsError('More than one book matching: %s' %
                                        ('; '.join([('%s - %s (%d)' % (bk[0], bk[1], idnum))
                                                     for idnum, bk in title_id_dict.items()])))
    elif not title_id_dict:
        raise AmbiguousArgumentsError('No books matching %s/%s found' %
                                        (args.author, args.title))

    title_id = title_id_dict.keys()[0]
    print(title_id)
    pubs = get_publications(conn, [title_id], verbose=args.verbose)
    """
    title_ids = get_title_ids(conn, args)
    if not title_ids:
        logging.error('No matching titles found')
        sys.exit(1)
    pubs = get_publications(conn, title_ids, verbose=args.verbose)
    render_details(pubs)

