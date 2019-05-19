#!/usr/bin/env python3
"""
Show all the different formats and countries a book was published in.
"""

from argparse import ArgumentParser
from collections import namedtuple, defaultdict
import logging
import pdb
import sys

from sqlalchemy.sql import text

from country_related import (derive_country_from_price)
from common import (get_connection, parse_args,
                    get_filters_and_params_from_args)
from isfdb_utils import convert_dateish_to_date
from title_related import get_title_ids

UNKNOWN_COUNTRY = 'XX'

PublicationDetails = namedtuple('PublicationDetails', 'type, format, date, isbn')

def get_publications(conn, title_ids, verbose=False, allowed_ctypes=None):
    """
    Return a dictionary mapping countries to a list of editions published
    there.  Countries are derived from price, so maybe be vague e.g. Eurozone
    publications.  (Possibly we might be able to derive country from publisher?)

    This takes a list of title_ids because it seems we have to use both the
    child and the parent to be sure of finding matching pubs
    """

    fltrs = ['pc.title_id IN :title_ids']
    if allowed_ctypes is not None:
        fltrs.append('p.pub_ctype IN :allowed_ctypes')

    query = text("""SELECT pub_ptype format,
                           pub_ctype type,
                           CAST(pub_year AS CHAR) dateish,
                           pub_isbn isbn,
                           pub_price price,
                           pc.title_id title_id
      FROM pub_content pc
      LEFT OUTER JOIN pubs p ON p.pub_id = pc.pub_id
      WHERE %s
        ORDER BY p.pub_year""" % (' AND '.join(fltrs)))
    results = conn.execute(query, title_ids=title_ids,
                           allowed_ctypes=allowed_ctypes)
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
        ret[country].append(PublicationDetails(row['type'].title(),
                                               row['format'],
                                               dt or None,
                                               row['isbn'] or None))
    return ret

def render_details(pubs, output_function=print):
    # print(pubs)
    for i, (country, details) in enumerate(sorted(pubs.items())):
        if i > 0:
            output_function()
        output_function('== %s (%d editions) ==\n' % (country, len(details)))
        for detail in details:
            output_function('* %-10s %10s published %-12s (ISBN:%s)' % (detail))


if __name__ == '__main__':
    args = parse_args(sys.argv[1:],
                      description='List publication countries and dates for a book',
                      supported_args='antv')

    conn = get_connection()
    title_ids = get_title_ids(conn, args)
    if not title_ids:
        logging.error('No matching titles found')
        sys.exit(1)
    pubs = get_publications(conn, title_ids, verbose=args.verbose)
    render_details(pubs)

