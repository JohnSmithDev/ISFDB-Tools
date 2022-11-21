#!/usr/bin/env python3
"""
Query and output stats based on primary verification of titles

"""

import pdb
import sys

from sqlalchemy.sql import text


from common import (get_connection, create_parser, parse_args,
                    get_filters_and_params_from_args)


def get_verification_stats(conn, args, limit=100):
    """
    Return a list/iterable of the most verified titles
    """

    cnm = {'year': 'title_copyright'}

    fltr, params = get_filters_and_params_from_args(args,
                                                    column_name_mappings=cnm)
    if fltr:
        fltr = f' WHERE {fltr}'

    if 'limit' not in params:
        params['limit'] = limit

    query = text("""
    WITH root_query AS (
      SELECT CASE WHEN t.title_parent !=0 THEN t.title_parent ELSE t.title_id END root_title_id,
        COUNT(1) num_verifications,
        COUNT(DISTINCT p.pub_id) num_verified_pubs,
        COUNT(DISTINCT pv.user_id) num_verifiers
      FROM primary_verifications pv
      NATURAL JOIN pubs p
      NATURAL JOIN pub_content pc
      LEFT OUTER JOIN titles t ON t.title_id = pc.title_id
      WHERE p.pub_ctype = t.title_ttype
      GROUP BY root_title_id
    )
    SELECT t.title_id, t.title_title, YEAR(t.title_copyright) year, t.title_ttype,
      GROUP_CONCAT(author_canonical SEPARATOR ' and ') authors,
      rq.num_verifications,  RANK() OVER (ORDER BY num_verifications DESC) num_verifications_rank,
      rq.num_verified_pubs, RANK() OVER (ORDER BY num_verified_pubs DESC) num_verified_pubs_rank,
      rq.num_verifiers, RANK() OVER (ORDER BY num_verifiers DESC) num_verifiers_rank
    FROM root_query rq
    INNER JOIN titles t ON rq.root_title_id = t.title_id
    LEFT OUTER JOIN canonical_author ca ON ca.title_id = t.title_id
    LEFT OUTER JOIN authors a ON a.author_id = ca.author_id
    %s
    GROUP BY t.title_id
    ORDER BY num_verifiers DESC, num_verifications DESC, num_verified_pubs DESC
    LIMIT :limit;"""  % (fltr))
    # pdb.set_trace()
    results = conn.execute(query, **params).fetchall()
    return results

def output_report(data, output_function=print):
    for i, row in enumerate(data, 1):
        output_function('%3d. %s' % (i, row))

if __name__ == '__main__':
    mconn = get_connection()
    parser = create_parser(description='Report on most frequently (primary) verified titles',
                           supported_args='ly')
    margs = parse_args(sys.argv[1:], parser=parser)

    data = get_verification_stats(mconn, margs)
    output_report(data)
