#!/usr/bin/env python3
"""
Query and output stats based on primary verification of titles

"""

import sys

from sqlalchemy.sql import text


from common import (get_connection, create_parser, parse_args,
                    get_filters_and_params_from_args)


def get_verification_stats(conn, filters):
    fltr, params = get_filters_and_params_from_args(args)

    query = text("""
    SELECT * FROM (
      SELECT pc.title_id, t.title_title, t.title_ttype,
        COUNT(1) num_verifications, COUNT(DISTINCT p.pub_id) num_pubs
      FROM primary_verifications pv
      NATURAL JOIN pubs p
      NATURAL JOIN pub_content pc
      LEFT OUTER JOIN titles t ON t.title_id = pc.title_id
      WHERE p.pub_ctype = t.title_ttype
      GROUP BY title_id
    ) foo
    ORDER BY num_verifications
    DESC LIMIT 100;""") #  % (fltr)) # TODO: restore filtering when properly configured

    results = conn.execute(query, **params).fetchall()
    return results

def output_report(data, output_function=print):
    for i, row in enumerate(data, 1):
        output_function('%3d. %s' % (i, row))

if __name__ == '__main__':
    mconn = get_connection()
    parser = create_parser(description='Report on most frequently (primary) verified titles',
                           supported_args='y')
    args = parse_args(sys.argv[1:], parser=parser)

    data = get_verification_stats(mconn, args)
    output_report(data)
