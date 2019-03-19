#!/usr/bin/env python3
"""
Report on the finalists (or winner, or longlist, if you use a symlinked version
of this script) of a particular award/category/year
"""

from collections import namedtuple
from os.path import basename
import pdb
import sys

from sqlalchemy.sql import text

from common import get_connection, parse_args, get_filters_and_params_from_args

# Do we need this, or can we use RowProxy directly?
AwardFinalist = namedtuple('AwardFinalist',
                           'title, author, rank, year, award, category')

def get_type_and_filter(txt):
    # TODO (probably): would be better/safer to return the award level number,
    # and only inject it into the query via SQLAlchemy
    if 'winner' in txt:
        typestring = 'winner'
        level_filter = 'award_level = 1'
    elif 'finalist' in txt:
        typestring = 'finalists'
        level_filter = 'award_level < 10'
    elif 'longlist' in txt:
        typestring = 'long list'
        level_filter = 'award_level < 100'
    else:
        raise Exception('Dunno how to handle script called %s' % (script_name))
    return typestring, level_filter


def get_finalists(conn, args, level_filter):

    fltr, params = get_filters_and_params_from_args(args)
    if level_filter:
        # TODO: this should be a proper param
        fltr += ' AND %s ' % level_filter

    # Hmm - award_level is a string, but currently only contains int values
    # (not even NULL), which means the sort doesn't work as expected without
    # the cast

    query = text("""SELECT award_title, award_author,
          CAST(award_level AS UNSIGNED) award_level,
          YEAR(award_year) year,
          at.award_type_name, ac.award_cat_name
      FROM awards a
        LEFT OUTER JOIN award_types at ON at.award_type_id = a.award_type_id
        LEFT OUTER JOIN award_cats ac ON ac.award_cat_id = a.award_cat_id
      WHERE %s ORDER BY year, CAST(award_level AS UNSIGNED)""" % fltr)
    #print(query)
    # pdb.set_trace()
    results = conn.execute(query, **params).fetchall()

    return [AwardFinalist(*z.values()) for z in results]



if __name__ == '__main__':
    script_name = basename(sys.argv[0])
    typestring, level_filter = get_type_and_filter(script_name)


    args = parse_args(sys.argv[1:],
                      description='Show %s for an award' % (typestring),
                      supported_args='cwy')

    conn = get_connection()
    award_results = get_finalists(conn, args, level_filter)
    for row in award_results:
        print(row)


