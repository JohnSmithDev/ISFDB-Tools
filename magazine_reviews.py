#!/usr/bin/env python3
"""
Report on all reviews in a magzine (or some other venue that ISFDB has records
on) over a period of time.
"""

import logging
import pdb
import sys

from sqlalchemy.sql import text

from common import (get_connection, create_parser, parse_args,
                    get_filters_and_params_from_args)
from isfdb_utils import convert_dateish_to_date

REVIEW_TTYPES_OF_INTEREST = ('REVIEW',)
WORK_TTYPES_OF_INTEREST = ('NOVEL',)


class ReviewedWork(object):
    def __init__(self, row):
        self.title = row['work_title']
        self.author = row['work_author']
        self.review_date = convert_dateish_to_date(row['review_month'])
        self.title_id = row['work_id']

    def __repr__(self):
        return '"%s" (title_id=%d) by %s reviewed %s' % (self.title,
                                                         self.title_id,
                                                         self.author,
                                                         self.review_date)



def get_reviews(conn, args):
    fltr, params = get_filters_and_params_from_args(
        args, column_name_prefixes={'year': 'pub'})


    # r_t.title_title and w_t.title_title are probably the same, however
    # they could be different e.g.
    # 2348413, 'Pride and prometheus', 'REVIEW', vs
    # 2300846, 'Pride and Prometheus', 'NOVEL'
    # w_t.title_title is likely to be better as it has higher visibility in
    # IMDB.
    query = text("""
SELECT r_pc.pub_id, r_pc.pubc_page, r_t.title_id,
    r_t.title_title, r_t.title_ttype,
    CAST(r_t.title_copyright as CHAR) review_month,
    tr.title_id work_id,
    w_t.title_title work_title, w_t.title_ttype,
    w_a.author_canonical work_author
FROM pub_content r_pc
left outer join titles r_t on r_t.title_id = r_pc.title_id
left outer join title_relationships tr on r_t.title_id = tr.review_id
left outer join titles w_t on w_t.title_id = tr.title_id
LEFT OUTER JOIN canonical_author w_ca ON w_ca.title_id = w_t.title_id
LEFT OUTER JOIN authors w_a ON w_ca.author_id = w_a.author_id
WHERE pub_id IN (
  select  p.pub_id from series s left outer join titles t on t.series_id = s.series_id
  left outer join pub_content pc on pc.title_id = t.title_id
  left outer join pubs p on p.pub_id = pc.pub_id
  where s.series_title = :magazine and %s
)
  AND r_t.title_ttype in :review_ttypes
  AND w_t.title_ttype in :work_ttypes
    ORDER BY review_month, pub_id, pubc_page;
""" % fltr)
    params['review_ttypes'] = REVIEW_TTYPES_OF_INTEREST
    params['work_ttypes'] = WORK_TTYPES_OF_INTEREST
    params['magazine'] = args.magazine
    results = conn.execute(query, **params).fetchall()
    return [ReviewedWork(z) for z in results]



if __name__ == '__main__':
    parser = create_parser(description='Show all reviews published in a magazine',
                           supported_args='y')
    # TODO: have this support the -m / -M pattern for pattern vs exact match
    parser.add_argument('-m', dest='magazine', nargs='?',
                       help='Exact name of magazine')
    args = parse_args(sys.argv[1:], parser=parser)


    conn = get_connection()
    reviews = get_reviews(conn, args)
    for row in reviews:
        print(row)

