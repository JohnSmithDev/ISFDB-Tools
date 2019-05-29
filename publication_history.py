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

from country_related import (derive_country_from_price, UNKNOWN_COUNTRY)
from common import (get_connection, parse_args,
                    get_filters_and_params_from_args)
from isfdb_utils import convert_dateish_to_date
from title_related import get_title_ids

XXX_UNKNOWN_COUNTRY = 'XX'

class PublicationDetails(object):
    def __init__(self, type_, format, dt, isbn):
        self.type = type_
        self.format = format
        self.date = convert_dateish_to_date(dt)
        # IIRC the next could be an empty string, so use None if so
        self.isbn = isbn or None

    def has_inconsistencies_with(self, other):
        # THIS HASN'T BEEN TESTED, BECAUSE I'VE YET TO FIND A REAL-WORLD EXAMPLE
        # (and I'm too lazy to have set up proper tests yet)
        # Date is woolly enough that I think it can be ignored here
        PROPERTIES_TO_CHECK = ['type', 'format']
        issues = []
        for prop in PROPERTIES_TO_CHECK:
            this = getattr(self, prop)
            that = getattr(other, prop)
            if this != that:
                issues.add('%s: %s != %s' % (prop, this, that))
        return issues


    def pretty(self):
        return '%-10s %10s published %-12s (ISBN:%s)' % (self.type.title(),
                                                         self.format,
                                                         self.date,
                                                         self.isbn)
    def __repr__(self):
        return '%s %s published %s (ISBN: %s)' % (self.type.title(),
                                                  self.format,
                                                  self.date,
                                                  self.isbn)

def create_publication_details_from_row(row):
    return PublicationDetails(row['type'], row['format'],
                              row['dateish'], row['isbn'])


def _get_publications(conn, title_ids, verbose=False, allowed_ctypes=None):
    """
    Engine for the get_publications_by_* functions, which do postprocessing
    on the raw rows this returns
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
    return results


def get_publications_by_country(conn, title_ids, verbose=False, allowed_ctypes=None):
    """
    Return a dictionary mapping countries to a list of editions published
    there.  Countries are derived from price, so maybe be vague e.g. Eurozone
    publications.  (Possibly we might be able to derive country from publisher?)

    This takes a list of title_ids because it seems we have to use both the
    child and the parent to be sure of finding matching pubs
    """

    # Q: Do we need the casting to list?
    rows = list(_get_publications(conn, title_ids, verbose, allowed_ctypes))
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
        ret[country].append(create_publication_details_from_row(row))
    return ret

def get_publications_by_isbn(conn, title_ids, verbose=False, allowed_ctypes=None,
                             log=logging):
    """
    Return a tuple of
    * a dict mapping ISBNs to PublicationDetails
    * a list of the PublicationDetails that don't have ISBNs (hopefully empty

    Note that if there are multiple publications that share the same ISBN,
    an arbitrary value will be returned.  However, there are some cursory
    checks done to see if the "duplicates" have inconsistent properties
    e.g. format, and these are logged.

    NB: at time of writing, I've not yet found any current cases where duplicate
    ISBNs have different type attributes.  I'm sure they exist though, as I
    recently fixed one (ebook using ISBN of a physical omnibus).

    The return value from this function is not particularly useful for output;
    it is more aimed at external code that takes this data and does more
    with it.
    """
    rows = _get_publications(conn, title_ids, verbose, allowed_ctypes)
    ret = {}
    isbnless = []
    for row in rows:
        pd = create_publication_details_from_row(row)
        if not pd.isbn:
            isbnless.append(pd)
            continue

        try:
            other = ret[pd.isbn]
            inconsistencies =  pd.has_inconsistencies_with(other)
            print(inconsistencies)
            if inconsistencies:
                log.warning(inconsistencies)
            # TODO (maybe): replace the value?
        except KeyError:
            ret[pd.isbn] = pd
            continue
    return ret, isbnless


def render_details(pubs, output_function=print):
    # print(pubs)
    for i, (country, details) in enumerate(sorted(pubs.items())):
        if i > 0:
            output_function()
        output_function('== %s (%d editions) ==\n' % (country, len(details)))
        for detail in details:
            output_function('* %s' % (detail.pretty()))


if __name__ == '__main__':
    args = parse_args(sys.argv[1:],
                      description='List publication countries and dates for a book',
                      supported_args='antv')

    conn = get_connection()
    title_ids = get_title_ids(conn, args)
    if not title_ids:
        logging.error('No matching titles found')
        sys.exit(1)
    pubs = get_publications_by_country(conn, title_ids, verbose=args.verbose)
    render_details(pubs)

