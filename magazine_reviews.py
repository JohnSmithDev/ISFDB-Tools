#!/usr/bin/env python3
"""
Report on all reviews in a magzine (or some other venue that ISFDB has records
on) over a period of time.

For reference, and because a query to get this from the DB is hard, these are
some review venues with a decent amnount of reviews:
* Locus (at time of writing, stops mid 2018)
* Interzone
* Strange Horizons
* The Magazine of Fantasy and Science Fiction (stops in 2015 though - or poss.
  name change in database?)

Magazines which are somewhat compromised:
* Vector (at time of writing, stops 2016; also, they don't have months for the
          review dates, this would have to be derived from the season in the
          issue name, which isn't always populated)
"""

from collections import defaultdict
from datetime import date
from enum import Enum
from functools import reduce
import logging
import pdb
import sys

from sqlalchemy.sql import text

from common import (get_connection, create_parser, parse_args,
                    get_filters_and_params_from_args)
from isfdb_utils import convert_dateish_to_date


class DuplicateReviewError(Exception):
    pass

class RepeatReviewBehaviour(Enum):
    ALLOW = 1,
    DIFFERENT_MONTHS_ONLY = 2,
    DIFFERENT_YEARS_ONLY = 3,
    DISALLOW = 4



REVIEW_TTYPES_OF_INTEREST = ('REVIEW',)
WORK_TTYPES_OF_INTEREST = ('NOVEL',)

pub_months = {} # This is an imperfect bodge for empty r_t.title_copyright

def normalize_month(dt):
    """
    Convert yyyy-mm-dd to yyyy-mm-01
    This is for sites like Strange Horizons that publish multiple reviews
    per month on different days.
    """
    if dt:
        return date(dt.year, dt.month, 1)
    else:
        return None

class ReviewedWork(object):
    _known_keys = {}

    def __init__(self, row, allow_duplicates=RepeatReviewBehaviour.ALLOW):
        self.title = row['work_title']
        self.authors = {row['work_author']}
        self.title_id = row['work_id']
        self.pub_id = row['pub_id']
        self.review_month = normalize_month(convert_dateish_to_date(row['review_month']))
        if self.review_month is None:
            # Maybe another review in this issue has the date?
            fallback = pub_months.get(row['pub_id'], None)
            logging.warning('Undefined review month for %s (review.title_id=%d,'
                            'work.title_id=%d), using fallback %s' %
                            (self.title, row['title_id'], self.title_id,
                             fallback))
            self.review_month = fallback
        else:
            pub_months[row['pub_id']] = self.review_month

        if allow_duplicates != RepeatReviewBehaviour.ALLOW:
            if allow_duplicates == RepeatReviewBehaviour.DIFFERENT_MONTHS_ONLY:
                dupe_key = (self.title_id, self.review_month)
            elif allow_duplicates == RepeatReviewBehaviour.DIFFERENT_YEARS_ONLY:
                dupe_key = (self.title_id, self.review_year)
            else: # allow_duplicates == RepeatReviewBehaviour.DISALLOW
                dupe_key = self.title_id
            if dupe_key in self._known_keys:
                # Possibly caused by multiple authors producing multiple rows,
                # in which case merge them back before aborting this object
                other = self._known_keys[dupe_key]
                other.authors.update(self.authors)

                raise DuplicateReviewError('Already have a review for %s (%s)' %
                                           (self.title, dupe_key))
            self._known_keys[dupe_key] = self


    @property
    def author(self):
        return '+'.join(sorted(self.authors))

    @property
    def review_year(self):
        return self.review_month.year

    def __repr__(self):
        return '"%s" (title_id=%d) by %s reviewed %s' % (self.title,
                                                         self.title_id,
                                                         self.author,
                                                         self.review_month)




def get_reviews(conn, args, repeats=RepeatReviewBehaviour.DIFFERENT_MONTHS_ONLY):
    fltr, params = get_filters_and_params_from_args(
        args, column_name_prefixes={'year': 'pub'})


    # r_t.title_title and w_t.title_title are probably the same, however
    # they could be different e.g.
    # 2348413, 'Pride and prometheus', 'REVIEW', vs
    # 2300846, 'Pride and Prometheus', 'NOVEL'
    # w_t.title_title is likely to be better as it has higher visibility in
    # IMDB.
    # The ordering by 'review_month DESC' is a hack to allow the pub_months
    # bodge to have a better chance of working.
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
    ORDER BY review_month DESC, pub_id, pubc_page;
""" % fltr)
    params['review_ttypes'] = REVIEW_TTYPES_OF_INTEREST
    params['work_ttypes'] = WORK_TTYPES_OF_INTEREST
    params['magazine'] = args.magazine
    results = conn.execute(query, **params).fetchall()

    def make_list_excluding_duplicates(accumulator, new_value):
        if not accumulator:
            accumulator = []
        try:
            accumulator.append(ReviewedWork(new_value,
                                            allow_duplicates=repeats))
        except DuplicateReviewError:
            pass
        return accumulator

    reviews = reduce(make_list_excluding_duplicates, results, None)
    return sorted(reviews, key=lambda z: z.review_month)





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

