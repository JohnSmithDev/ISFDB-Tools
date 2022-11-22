#!/usr/bin/env python3
"""
Query and output stats based on primary verification of titles

"""

from collections import Counter

import pdb
import sys

from sqlalchemy.sql import text


from common import (get_connection, create_parser, parse_args,
                    get_filters_and_params_from_args)


def get_verification_stats(conn, args, limit=100, author_separator=' and '):
    """
    Return a list/iterable of the most verified titles
    """

    cnm = {'year': 'title_copyright'}

    fltr, params = get_filters_and_params_from_args(args,
                                                    column_name_mappings=cnm)
    if fltr:
        fltr = f' WHERE {fltr}'

    if 'limit' not in params or not params['limit']:
        params['limit'] = limit

    params['author_separator'] = author_separator

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
      GROUP_CONCAT(author_canonical ORDER BY author_canonical SEPARATOR :author_separator) authors,
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

def extra_stats(data, output_function=print):

    def output_counter(heading, c, limit=20):
        output_function(f'== {heading} ==')
        for i, stuff in enumerate(c.most_common(limit), 1):
            output_function('%2d. %-40s : %3d' % (i, stuff[0], stuff[1]))
        output_function()

    author_stats = Counter([z.authors for z in data])
    output_counter('Top authors by number of top verified titles', author_stats)

    type_stats = Counter([z.title_ttype for z in data])
    output_counter('Top types by number of top verified titles', type_stats)

    year_stats = Counter([z.year for z in data])
    output_counter('Top years by number of top verified titles', year_stats)

    def decade(year):
        return '%s0s' % (str(year)[:3])

    decade_stats = Counter([decade(z.year) for z in data])
    output_counter('Top decades by number of top verified titles', decade_stats)


if __name__ == '__main__':
    mconn = get_connection()
    parser = create_parser(description='Report on most frequently (primary) verified titles',
                           supported_args='ly')
    parser.add_argument('-x', dest='extra_stats', action='store_true',
                        help='Show extra stats derived from the basic data')
    margs = parse_args(sys.argv[1:], parser=parser)

    mdata = get_verification_stats(mconn, margs)
    output_report(mdata)

    if margs.extra_stats:
        extra_stats(mdata)
