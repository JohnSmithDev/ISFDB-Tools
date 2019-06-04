#!/usr/bin/env python3
"""
Show what categories an award presents, possibly filtered on a particular year.
"""

from datetime import date
from collections import defaultdict
from os.path import basename
import pdb
import sys

from sqlalchemy.sql import text

from common import get_connection, parse_args, get_filters_and_params_from_args

class AwardCategory(object):
    """
    Basically a namedtuple with a nicer __repr__ and some derived properties
    """

    def __init__(self, row):
        self.award = row['award_type_name']
        self.category = row['award_cat_name']
        self.year_from = row['from_year']
        self.year_to = row['to_year']

    @property
    def isfdb_url(self):
        pass # TODO

    @property
    def pretty_year_range(self):
        if self.year_from == self.year_to:
            year_bit = self.year_from
        else:
            if self.year_to == this_year:
                # This logic is maybe dubious if this year's awards
                # haven't been nominated/presented yet - but I don't know
                # how we could discriminate between that, and a category
                # which finished last year.
                year_bit = '%s-present' % (self.year_from)
            else:
                year_bit = '%d-%d' % (self.year_from, self.year_to)
        return year_bit

    def __repr__(self):
        return '%s %s running %s' % (self.award, self.category,
                                     self.pretty_year_range)

def get_award_categories(conn, args):
    """
    Return a list of [(award_name, [award_categories]), ...] matching args
    """
    fltr, params = get_filters_and_params_from_args(args)

    query = text("""SELECT  award_type_name, award_cat_name,
         MIN(YEAR(award_year)) from_year, MAX(YEAR(award_year)) to_year
         -- GROUP_CONCAT(CAST(award_year AS CHAR) SEPARATOR ',') years
       FROM awards a
         LEFT OUTER JOIN award_types at ON at.award_type_id = a.award_type_id
         LEFT OUTER JOIN award_cats ac ON ac.award_cat_id = a.award_cat_id
       WHERE %s
       GROUP BY award_type_name, award_cat_name
       ORDER BY award_type_name, award_cat_name
       """ % fltr)
    # print(query)
    results = conn.execute(query, **params).fetchall()

    # Could this conversion be done more pythonically? (zip, itertools perhaps?)
    raw_dict = defaultdict(list)
    ORIG = """
    for award, cat, from_year, to_year in results:
    # for award, cat, years in results:
        raw_dict[award].append((cat, from_year, to_year))
        # raw_dict[award].append((cat, years))
    """
    for row in results:
        ac_obj = AwardCategory(row)
        raw_dict[ac_obj.award].append(ac_obj)

    ret = sorted(raw_dict.items())
    return ret

def render_year_ranges(year_list_string):
    # This probabky works, except that MySQL truncates GROUP_CONCAT to 1024 chars.
    # Can be overridden at a system/session level, but not really viable here?
    # https://dev.mysql.com/doc/refman/8.0/en/group-by-functions.html#function_group-concat
    # print(len(year_list_string))
    unique_pseudo_dates = set(year_list_string.split(','))
    years = sorted([int(z.split('-')[0]) for z in unique_pseudo_dates])
    # I thought I had a nice function elsewhere to do the next bit,
    # but I can't find it (or the code that I have found is much less nice
    # than I thought...)
    if len(years) == 1:
        return '%s' % (years[0])
    # print(years)
    bits = []
    prev = range_start = years[0]
    in_range = False
    for this_year in years[1:]:
        if this_year == prev + 1:
            prev = this_year
            in_range = True
        else:
            if in_range:
                bits.append('%d-%d' % (range_start, prev))
            else:
                bits.append('%d' % (range_start))
            range_start = prev = this_year
            in_range = False

    if in_range:
        bits.append('%d-%d' % (range_start, prev))
    else:
        bits.append('%d' % (range_start))
    ret = (','.join(bits))
    # print(ret)
    return ret


if __name__ == '__main__':
    this_year = date.today().year
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
            # year_bit = render_year_ranges(cat[1])
            print('* %s (%s)' % (cat.category, cat.pretty_year_range))



