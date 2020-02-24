#!/usr/bin/env python3
"""
Report on the finalists (or winner, or longlist, if you use a symlinked version
of this script) of a particular award/category/year.

Also functions that can be used as a library call for more in-depth award-
related reports.
"""

from collections import namedtuple
import json
from os.path import basename, dirname
import os
import pdb
import sys

from sqlalchemy.sql import text

from common import (get_connection, parse_args, get_filters_and_params_from_args,
                    create_parser)
from isfdb_utils import pretty_nth
from award_related import (BOGUS_AUTHOR_NAMES, DODGY_TITLES_AND_PSEUDO_AUTHORS,
                           EXCLUDED_AUTHORS,
                           load_category_groupings)


XXX_AwardFinalist = namedtuple('XXX_AwardFinalist',
                           'title, author, rank, year, award, category, award_id, title_id')

class AwardFinalist(object):
    def __init__(self, title, author, rank, year, award, category,
                 award_id, title_id):
        self.title = title
        self.author = author
        self.rank = rank
        self.year = year
        self.award = award
        self.category = category
        self.award_id = award_id
        self.title_id = title_id

    @property
    def dict_for_csv_output(self):
        return {
            'year': self.year,
            'award': self.award,
            'category': self.category,
            'rank': self.rank,
            'author': self.author,
            'title': self.title
            }

    def __repr__(self):
        return '"%s" by %s (title_id=%s), %s in the %d %s for %s' % \
            (self.title, self.author, self.title_id,
             pretty_nth(self.rank), self.year, self.award, self.category)


MOVED = """
CATEGORY_CONFIG = os.path.join(dirname(__file__), 'category_groupings.json')
with open(CATEGORY_CONFIG) as inputstream:
    CATEGORY_GROUPINGS = json.load(inputstream)
"""

CATEGORY_GROUPINGS = load_category_groupings()

def get_type_and_filter(txt):
    # TODO (probably): would be better/safer to return the award level number,
    # and only inject it into the query via SQLAlchemy
    if 'winner' in txt:
        typestring = 'winner'
        level_filter = 'award_level = 1'
    elif 'finalist' in txt:
        typestring = 'finalists'
        # 90 is the right value for Hugos (see 1974 and 1975), not sure about other
        # awards
        level_filter = '(award_level <= 10 or award_level = 90)'
    elif 'longlist' in txt:
        typestring = 'long list'
        level_filter = 'award_level < 100'
    else:
        raise Exception('Dunno how to handle script called %s' % (script_name))
    return typestring, level_filter


def get_finalists(conn, args, level_filter, ignore_no_award=True):
    """
    Not just finalists, set level_filter to pick up winners or shortlists etc
    as desired.
    """

    fltr, params = get_filters_and_params_from_args(args)
    if level_filter:
        # TODO: this should be a proper param
        fltr += ' AND %s ' % level_filter

    # Hmm - award_level is a string, but currently only contains int values
    # (not even NULL), which means the sort doesn't work as expected without
    # the cast.
    # award_id and title_id are for use by any other code that builds upon this
    # output (although I don't know if award_id is used anywhere outside of
    # awards and title_awards?)

    query = text("""SELECT award_title, award_author,
          CAST(award_level AS UNSIGNED) award_level,
          YEAR(award_year) year,
          at.award_type_name, ac.award_cat_name,
          a.award_id, ta.title_id
      FROM awards a
        LEFT OUTER JOIN award_types at ON at.award_type_id = a.award_type_id
        LEFT OUTER JOIN award_cats ac ON ac.award_cat_id = a.award_cat_id
        LEFT OUTER JOIN title_awards ta ON ta.award_id = a.award_id
      WHERE %s ORDER BY year, CAST(award_level AS UNSIGNED)""" % fltr)
    #print(query)
    # pdb.set_trace()
    results = conn.execute(query, **params).fetchall()

    finalists = []
    for row in results:
        # The title/DODGY... and author/EXCLUDED checks will likely always
        # have the same value, but better safe than sorry.
        # print(row['award_author'])
        if ignore_no_award and \
           (row['award_title'] in DODGY_TITLES_AND_PSEUDO_AUTHORS or
            row['award_author'] in EXCLUDED_AUTHORS):
            continue
        finalists.append(AwardFinalist(*row.values()))
    return finalists
    # return [AwardFinalist(*z.values()) for z in results]


    WIP_HACKERY = """
    ret = []
    for z in results:
        if z['award_cat_name'] in CATEGORY_GROUPINGS['Hugo Award']['written-fiction']:
            ret.append(AwardFinalist(*z.values()))
    return ret
    """


if __name__ == '__main__':
    script_name = basename(sys.argv[0])
    typestring, level_filter = get_type_and_filter(script_name)


    parser = create_parser(description='Show %s for an award' % (typestring),
                           supported_args='cwy')
    parser.add_argument('-k', dest='csv_file', nargs='?',
                        help='Output as CSV to named file (default is human-readable output)')

    args = parse_args(sys.argv[1:], parser=parser)

    conn = get_connection()
    award_results = get_finalists(conn, args, level_filter)
    if args.csv_file:
        from csv import DictWriter
        with open(args.csv_file, 'w') as outputstream:
            writer = DictWriter(outputstream, ['year', 'award', 'category',
                                               'rank', 'author', 'title'])
            for finalist in award_results:
                writer.writerow(finalist.dict_for_csv_output)
    else:
        for row in award_results:
            print(row)


