#!/usr/bin/env python3
"""
Output all (or some) volumes in a series
"""


from collections import namedtuple
from datetime import date
from enum import Enum
import pdb
import re
import sys

from sqlalchemy.sql import text

from common import get_connection
from isfdb_utils import convert_dateish_to_date, safe_year_from_date

# I'm not sure what title_seriesnum_2 is - only one populated I've found so far
# is The Furthest Station in Rivers of London.
# UPDATE: http://www.isfdb.org/wiki/index.php/Schema:titles says
# "title_seriesnum_2 - The part of the series number to the right of the
#  decimal point (if one is present.)"
# Note that title_seriesnum_2 is a varchar, not an int - although as of May
# 2019, all values are int()able - see
#    select distinct title_seriesnum_2, count(1) from titles
#       group by title_seriesnum_2 order by title_seriesnum_2;

# title_seriesnum seems to be NULL/None for omnibus, extracts,
# (some) short fiction, etc
# It doesn't seem to be guaranteed to be consecutive - e.g. Discworld
# (series_id=186) doesn't have volumes 28, 30, 32, 35 or 38
# (Turns out they are in the "Discoworld - Children's" (sub)series)
XXX__SeriesTitleDetails = namedtuple('SeriesTitleDetails',
                                'title_id, title, type, seriesnum, seriesnum_2')


class SeriesTitleDetails(object):
    def __init__(self, row_dict, subseries_info=None):
        # print(row_dict)
        self.title_id = row_dict['title_id']
        self.title = row_dict['title']
        self.type = row_dict['type']
        self.seriesnum = row_dict['seriesnum']
        self.seriesnum_2 = row_dict['seriesnum_2']
        self.copyright_date = convert_dateish_to_date(row_dict['copyright_dateish'])
        self.series_id = row_dict['series_id']
        self.series_name = row_dict['series_name']
        self.subseries_info = subseries_info

    @property
    def year(self):
        return safe_year_from_date(self.copyright_date)

    @property
    def sortable_copyright_date(self):
        if not self.copyright_date:
            # Assume that dateless-less books are more likely to be older than
            # newer
            return date(1,1,1)
        else:
            return self.copyright_date


    @property
    def sortable_year(self):
        try:
            return self.copyright_date.year
        except AttributeError:
            # Assume that year-less books are more likely to be older than
            # newer
            return 0


    @property
    def overall_seriesnum(self):
        if not self.subseries_info:
            return None
        subseries_offset = self.subseries_info[self.series_id][3]
        if subseries_offset is None or \
           not self.subseries_info or len(self.subseries_info) == 1:
            return None
        else:
            return subseries_offset

    @property
    def series_sort_value(self):
        osn = self.overall_seriesnum
        # See earlier note about all current values are int()able (except
        # for None/Null, which we handle here).  My suspicion is that "25",
        # "75" etc would be better number sorted as if they were 2.5 or 7.5, but
        # this starts to get more complicated than I can be bothered to deal
        # with.
        try:
            safe_minor_value = int(self.seriesnum_2)
        except TypeError:
            safe_minor_value = 0
        safe_major_value = self.seriesnum or 0 # Perry Rhodan has some needing this, not sure why
        if not osn:
            return (safe_major_value, safe_minor_value, 0)
        else:
            return (osn, safe_major_value, safe_minor_value)

    @property
    def pretty_number(self):
        if not self.seriesnum:
            major = 'X'
        else:
            major = str(self.seriesnum)
        if self.seriesnum_2:
            return '%s.%s' % (major, self.seriesnum_2)
        else:
            return major

    def __repr__(self):
        if not self.subseries_info or len(self.subseries_info) == 1:
            # Don't need it if they are all the same
            series_name = ''
        else:
            series_name = self.series_name
        # TODO (nice to have): don't print two sets of volume numbers if
        # there are no subseries or minor-volumes.  This would require
        # knowledge of the other books in the series, which I think is asking
        # too much of a __repr__ method.
        return '%s #%s: %s [%s] (title_id=%d)' % (series_name,
                                                  self.pretty_number,
                                                  self.title,
                                                  self.year,
                                                  self.title_id)

# The downside of INCLUDE_ONLY_IF_ALL_UNNUMBERED is that (at least based on
# Hainish) it treats regular volumes the same as short stories, anthologies,
# omnibuses etc
class UnnumberedHandling(Enum):
    ALWAYS_INCLUDE = 1,
    ALWAYS_REJECT = 2,
    INCLUDE_ONLY_IF_ALL_UNNUMBERED = 3 # e.g. Hainish has no numbered volumes


def get_series_id(conn, series_name):
    query = text("""SELECT series_id, series_title
    FROM series
    WHERE series_title = :series_name;""")
    # Q: are series_title values unique?  (If they aren't, this script may
    # need to take new options?)
    results = conn.execute(query, {'series_name': series_name}).fetchall()
    if len(results) == 1:
        return results[0]['series_id']
    else:
        raise Exception('Got %d rows querying for "%s", expected 1 (%s)' %
                        (len(results), series_name,
                         ' / '.join([('%d:%s' % z) for z in results])))


def get_subseries_ids(conn, series_id):
    """
    Note that this will include the parent series itself.

    It doesn't (currently? get parents or grandchildren - although I dunno
    if there are genuine examples of the latter?
    """
    query = text("""SELECT series_id, series_parent,
        series_title, series_parent_position
    FROM series
    WHERE series_id = :series_id
     OR series_parent = :series_id;""")

    results = conn.execute(query, {'series_id': series_id}).fetchall()
    id_to_details = dict([(row.series_id, row) for row in results])
    return id_to_details

def get_titles_for_series_id(conn, series,
                             get_child_series=True,
                             ignore_unnumbered=UnnumberedHandling.ALWAYS_REJECT):
    """
    You might be better off calling get_series() rather than this, unless you
    have such a long series (e.g. Perry Rhodan?) that the sorting overhead is
    non-trivial.

    Given the name or ID of a series, return a list of SeriesTitleDetails

    series argument can be name or ID - determined by whether the argument is
    integer or not.  (Note that the other functions in this module take name
    or ID, but not both.)
    ignore_unnumbered is an UnnumberedHandling value.

    TODO: optional filtering on pub type, which will mitigate some issues with
    INCLUDE_ONLY_IF_ALL_UNNUMBERED.

    """
    if get_child_series:
        if isinstance(series, int):
            parent_series_id = series
        else:
            parent_series_id = get_series_id(conn, series)
        all_series = get_subseries_ids(conn, parent_series_id)
        all_series_ids = list(all_series.keys()) # avoid pain with dict_keys() object later
        params = {'all_series_ids': all_series_ids}
        fltr = ['s.series_id IN :all_series_ids']
    else:
        # This could be done more simply by tweaks to the above bit - but
        # perhaps this is more efficient.  (Does MySQL have an optimizer that
        # knows 'foo IN [single-value]' is 'foo - single-value'?
        if isinstance(series, int):
            params = {'series_id': series}
            fltr = ['s.series_id = :series_id']
        else:
            params = {'series_title': series}
            fltr = ['s.series_title = :series_title']
        all_series = None
        all_series_ids = None

    if ignore_unnumbered == UnnumberedHandling.ALWAYS_REJECT:
        fltr.append('title_seriesnum IS NOT NULL')
    fltrs = ' AND '.join(fltr)

    # Note that the order returned by this query doesn't handle subseries
    # well.  That is (optionally) addressed on the Python side of things
    query = text("""SELECT title_id, title_title title, title_ttype type,
      t.series_id series_id, s.series_title series_name,
      title_seriesnum seriesnum, title_seriesnum_2 seriesnum_2,
      CAST(title_copyright AS CHAR) copyright_dateish
    FROM titles t
    LEFT OUTER JOIN series s ON s.series_id = t.series_id
    WHERE %s
    ORDER BY title_seriesnum, title_seriesnum_2;""" % fltrs)

    results = conn.execute(query, **params).fetchall()
    titles = [SeriesTitleDetails(z, subseries_info=all_series) for z in results]
    if ignore_unnumbered == UnnumberedHandling.INCLUDE_ONLY_IF_ALL_UNNUMBERED:
        titles_with_numbers = [z for z in titles if z.seriesnum is not None]
        if len(titles_with_numbers) != len(titles):
            return titles_with_numbers
    return titles

def sort_by_volume_number(z):
    return z.series_sort_value

def sort_by_year(z):
    return z.year


def get_series(conn, series, get_child_series=True,
               ignore_unnumbered=UnnumberedHandling.ALWAYS_REJECT,
               sort_method=sort_by_volume_number):
    """
    See get_titles_for_series_id for docs on arguments and return value.
    """
    raw_data = get_titles_for_series_id(conn, series, get_child_series,
                                        ignore_unnumbered=UnnumberedHandling)

    data = sorted(raw_data, key=sort_by_volume_number)
    return data

if __name__ == '__main__':
    conn = get_connection()

    try:
        # Let's hope there aren't any series whose name is just numbers...
        series = int(sys.argv[1])
    except ValueError:
        series = sys.argv[1]

    # TODO: argument(s) to choose between different sort methods and
    # handling of unnumbered volumes
    # TODO: all code to implement optional filtering of certain pub types

    data = get_series(conn, series)
    for i, item in enumerate(data, 1):
        print('%2d. %s' % (i, item))


