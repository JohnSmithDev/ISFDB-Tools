#!/usr/bin/env python

# import logging
# import re
import sys

from sqlalchemy.sql import text

from country_related import get_country
from common import (get_connection, parse_args, get_filters_and_params_from_args,
                    AmbiguousArgumentsError)


def get_birthplaces_for_pseudonym(conn, author_id):
    """
    Examples:
    Mira Grant (author_id=133814) is Seanan McGuire (129348)
    James S. A. Corey (author_id=155601) is Ty Franck (author_id=123977) + Daniel Abraham (10297)
    """
    query = text("""SELECT a.author_id, author_canonical, author_birthplace
        FROM pseudonyms p
        LEFT OUTER JOIN authors a ON p.author_id = a.author_id
        WHERE pseudonym = :pseudonym_id""")
    results = conn.execute(query, pseudonym_id=author_id).fetchall()
    if results:
        return [z['author_birthplace'] for z in results]
    else:
        return None


def get_author_country(conn, filter_args, check_pseudonyms=True):
    fltr, params = get_filters_and_params_from_args(filter_args)

    query = text("""select author_id, author_canonical, author_birthplace
      from authors a
      where %s""" % fltr)
    results = conn.execute(query, **params).fetchall()

    if not results:
        # logging.error('No author found matching %s' % (filter_args))
        return None
    elif len(results) > 1:
        raise AmbiguousArgumentsError('Multiple (%d) authors matching %s: %s...' %
                                        (len(results), filter_args, results[:5]))
    else:
        rec = results[0]
        birthplace = rec['author_birthplace']
        if not birthplace and check_pseudonyms:
            bps = get_birthplaces_for_pseudonym(conn, rec['author_id'])
            if bps:
                return ','.join([get_country(z) for z in bps])
        return get_country(birthplace)



if __name__ == '__main__':
    args = parse_args(sys.argv[1:], description='Report birth country of author',
                      supported_args='a')

    conn = get_connection()
    print(get_author_country(conn, args))
