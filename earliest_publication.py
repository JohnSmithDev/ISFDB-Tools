#!/usr/bin/env python
"""
Show all the different formats and countries a book was published in.

(The script name is a bit of misnomer.  TODO: rename it.)

"""

from argparse import ArgumentParser
from collections import namedtuple, defaultdict
import logging
import pdb
import re
import sys

from sqlalchemy.sql import text

from country_related import (derive_country_from_price, get_country)
from common import get_connection
from common import (get_connection, parse_args,
                    get_filters_and_params_from_args,
                    AmbiguousArgumentsError)

AuthorBook = namedtuple('AuthorBook', 'author, book')

def get_title_id(conn, filter_args):
    filter, params = get_filters_and_params_from_args(filter_args)

    # This query isn't right - it fails to pick up "Die Kinder der Zeit"
    # The relevant ID is 1856439, not sure what column name that's for
    # Hmm, that's the correct title_id, perhaps there's more to it...

    # https://docs.sqlalchemy.org/en/latest/core/tutorial.html#using-textual-sql
    query = text("""select t.title_id, author_canonical author, title_title title, title_parent
      from titles t
      left outer join canonical_author ca on ca.title_id = t.title_id
      left outer join authors a on a.author_id = ca.author_id
      where %s AND
        title_ttype in ('NOVEL', 'CHAPBOOK', 'ANTHOLOGY', 'COLLECTION', 'SHORTFICTION')""" % (filter))

    # print(query)

    results = list(conn.execute(query, **params).fetchall())
    title_ids = set([z[0] for z in results])
    ret = {}
    for bits in results:
        # Exclude rows that have a parent that is in the results (I think these
        # are typically translations)
        # TODO: merge these into the returned results
        if not bits[3] and bits[3] not in title_ids:
            ret[bits[0]] = AuthorBook(bits[1], bits[2])
    return ret



def get_publications(title_id):
    query = text("""select *
      from pub_content pc
      left outer join pubs p on p.pub_id = pc.pub_id
      where pc.title_id = :title_id
        order by p.pub_year""")
    results = conn.execute(query, title_id=title_id)
    rows = list(results)
    ret = defaultdict(list)
    for row in rows:
        # print(row['pub_price'])
        country = derive_country_from_price(row['pub_price'])
        if not country:
            country = 'Unknown'
        # Hmm, Childhood's End has a load of None values, that don't show up
        # on the website
        # print(row['pub_year'])
        ret[country].append((row['pub_ptype'],
                             row['pub_year'] or 'Unknown Date',
                             row['pub_isbn'] or 'Unknown'))
    return ret




if __name__ == '__main__':
    args = parse_args(sys.argv[1:],
                      description='List publication countries and dates for a book',
                      supported_args='at')

    conn = get_connection()


    title_id_dict = get_title_id(conn, args)


    if len(title_id_dict) > 1:
        raise AmbiguousArgumentsError('More than one book matching: %s' %
                                        ('; '.join([('%s - %s' % z)
                                                    for z in title_id_dict.values()])))
    elif not title_id_dict:
        raise AmbiguousArgumentsError('No books matching %s/%s found' %
                                        (args.author, args.title))

    title_id = title_id_dict.keys()[0]
    pubs = get_publications(title_id)
    for country, details in pubs.items():
        print(country)
        for detail in details:
            print('%10s published %-12s (ISBN:%s)' % (detail))
