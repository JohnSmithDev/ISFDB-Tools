#!/usr/bin/env python3

from os.path import basename
import pdb
import sys

from sqlalchemy.sql import text

from common import get_connection, parse_args, get_filters_and_params_from_args





if __name__ == '__main__':
    script_name = basename(sys.argv[0])
    if 'winner' in script_name:
        typestring = 'winner'
        level_filter = 'award_level = 1'
    elif 'finalist' in script_name:
        typestring = 'finalists'
        level_filter = 'award_level < 10'
    elif 'longlist' in script_name:
        typestring = 'long list'
        level_filter = 'award_level < 100'
    else:
        raise Exception('Dunno how to handle script called %s' % (script_name))

    args = parse_args(sys.argv[1:],
                      description='Show %s for an award' % (typestring),
                      supported_args='cwy')

    conn = get_connection()
    fltr, params = get_filters_and_params_from_args(args)
    if level_filter:
        # TODO: this should be a proper param
        fltr += ' AND %s ' % level_filter

    # print(fltr)
    # print(params)

    # sys.exit(1)
    query = text("""SELECT award_title, YEAR(award_year) year, award_level FROM awards a
      LEFT OUTER JOIN award_types at ON at.award_type_id = a.award_type_id
      LEFT OUTER JOIN award_cats ac ON ac.award_cat_id = a.award_cat_id
      WHERE %s ORDER BY year, award_level""" % fltr)
    #print(query)
    # pdb.set_trace()
    results = conn.execute(query, **params).fetchall()
    for row in results:
        print(row)


