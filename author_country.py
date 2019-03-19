#!/usr/bin/env python

# import logging
# import re
import sys

from sqlalchemy.sql import text

from country_related import get_country
from common import (get_connection, parse_args, get_filters_and_params_from_args,
                    AmbiguousArgumentsError)

def get_author_country(conn, filter_args):
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
        return get_country(results[0]['author_birthplace'])



if __name__ == '__main__':
    args = parse_args(sys.argv[1:], 'a')

    conn = get_connection()
    print(get_author_country(conn, args))
