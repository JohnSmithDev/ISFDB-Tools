#!/usr/bin/env python3
"""
Show what categories an award presents, possibly filtered on a particular year.
"""

from collections import defaultdict
from os.path import basename
import pdb
import sys

from sqlalchemy.sql import text

from common import get_connection, parse_args, get_filters_and_params_from_args


def get_award_categories(conn, args):
    """
    Return a list of [(award_name, [award_categories]), ...] matching args
    """
    fltr, params = get_filters_and_params_from_args(args)

    query = text("""SELECT DISTINCT award_type_name, award_cat_name
       FROM awards a
         LEFT OUTER JOIN award_types at ON at.award_type_id = a.award_type_id
         LEFT OUTER JOIN award_cats ac ON ac.award_cat_id = a.award_cat_id
       WHERE %s
       ORDER BY award_type_name, award_cat_name
       """ % fltr)
    results = conn.execute(query, **params).fetchall()

    # Could this conversion be done more pythonically? (zip, itertools perhaps?)
    raw_dict = defaultdict(list)
    for award, cat in results:
        raw_dict[award].append(cat)
    ret = sorted(raw_dict.items())
    return ret


if __name__ == '__main__':
    args = parse_args(sys.argv[1:],
                      description='Show categories for an award',
                      supported_args='cwy')
    conn = get_connection()
    results = get_award_categories(conn, args)
    for i, (award, cats) in enumerate(results):
        if i > 0:
            print()
        print('= %s =' % (award))
        for cat in cats:
            print('* %s' % (cat))



