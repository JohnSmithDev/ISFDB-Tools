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

def convert_list_string_to_unique_years(year_list_string):
    unique_pseudo_dates = set(year_list_string.split(','))
    years = sorted([int(z.split('-')[0]) for z in unique_pseudo_dates if z])
    return years


def render_year_ranges(years, range_link='-', range_separator=', '):
    """
    Given an iterable of sorted years, return a prettier string of the distinct ranges e.g.

    >>>> render_year_ranges([2000,2005,2006,2008,2015,2016])
    '2000,2005-2008,2015-2016'

    Use convert_list_string_to_unique_years() to preprocess the data first if necessary)
    """

    # This probably works, except that MySQL truncates GROUP_CONCAT to 1024 chars.
    # (Bear in mind the query will return one date/year for each finalist, so whilst you
    # might have ~50 distinct years for long running awards, that needs multiplying by the
    # number of finalists (5 say) and then by the string length)
    # Can be overridden at a system/session level, but not really viable here?
    # https://dev.mysql.com/doc/refman/8.0/en/group-by-functions.html#function_group-concat
    # Update has been massively increased to 1M in MariaDB 10.2.4 per
    # https://database.guide/mariadb-group_concat/
    # Although re-reading the docs, you can do GROUP_CONCAT(DISTINCT ...) which should
    # avoid the problem for any version.

    if len(years) == 0:
        return ''
    if len(years) == 1:
        return '%s' % (years[0])
    bits = []
    prev = range_start = years[0]
    in_range = False
    for this_year in years[1:]:
        if this_year == prev + 1:
            prev = this_year
            in_range = True
        else:
            if in_range:
                bits.append('%d%s%d' % (range_start, range_link, prev))
            else:
                bits.append('%d' % (range_start))
            range_start = prev = this_year
            in_range = False

    if in_range:
        bits.append('%d%s%d' % (range_start, range_link, prev))
    else:
        bits.append('%d' % (range_start))
    ret = (range_separator.join(bits))
    return ret


class AwardCategory(object):
    """
    Basically a namedtuple with a nicer __repr__ and some derived properties
    """

    def __init__(self, row):
        self.award = row.award_type_name
        self.category = row.award_cat_name
        self.year_from = row.from_year
        self.year_to = row.to_year
        self.all_years = row.all_years

    @property
    def isfdb_url(self):
        pass # TODO

    @property
    def numeric_years(self):
        """
        Return the years as a sorted list of ints with no dupes
        """
        return convert_list_string_to_unique_years(self.all_years)

    @property
    def pretty_year_range(self):
        return render_year_ranges(self.numeric_years)

    def __repr__(self):
        return '%s %s running %s' % (self.award, self.category,
                                     self.pretty_year_range)

def get_award_categories(conn, args):
    """
    Return a list of [(award_name, [award_categories]), ...] matching args
    """
    fltr, params = get_filters_and_params_from_args(args)

    query = text("""SELECT award_type_name, award_cat_name,
         MIN(YEAR(award_year)) from_year, MAX(YEAR(award_year)) to_year,
         GROUP_CONCAT(DISTINCT CAST(YEAR(award_year) AS CHAR) SEPARATOR ',') all_years
       FROM awards a
         LEFT OUTER JOIN award_types at ON at.award_type_id = a.award_type_id
         LEFT OUTER JOIN award_cats ac ON ac.award_cat_id = a.award_cat_id
       WHERE %s
       GROUP BY award_type_name, award_cat_name
       ORDER BY award_type_name, award_cat_name
       """ % fltr)
    # print(query)
    results = conn.execute(query, params).fetchall()

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



if __name__ == '__main__':
    this_year = date.today().year
    args = parse_args(sys.argv[1:],
                      description='Show categories for an award',
                      supported_args='cwy')
    conn = get_connection()
    results = get_award_categories(conn, args)

    min_year = 9999
    max_year = -9999
    all_years = set()

    for i, (award, cats) in enumerate(results):
        if i > 0:
            print()
        print('= %s =' % (award))
        for cat in cats:
            print('* %s [%s]' % (cat.category, cat.pretty_year_range))
            min_year = min(cat.year_from, min_year)
            max_year = max(cat.year_to, max_year)
            all_years.update(cat.numeric_years)

    potential_years = set(range(min_year, max_year))
    missing_years = potential_years - all_years # set difference

    if missing_years:
        missing_string = render_year_ranges(sorted(missing_years))
        print(f'\n# There are no awards on record for the years {missing_string}')

