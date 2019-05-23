#!/usr/bin/env python3

from collections import namedtuple
from enum import Enum
import pdb
import re
import sys

from sqlalchemy.sql import text

from common import get_connection

# I'm not sure what title_seriesnum_2 is - only one populated I've found so far
# is The Furthest Station in Rivers of London.
# UPDATE: http://www.isfdb.org/wiki/index.php/Schema:titles says
# "title_seriesnum_2 - The part of the series number to the right of the
#  decimal point (if one is present.)"
# Note that title_seriesnum_2 is a varchar, not an int

# title_seriesnum seems to be NULL/None for omnibus, extracts,
# (some) short fiction, etc
# It doesn't seem to be guaranteed to be consecutive - e.g. Discworld
# (series_id=186) doesn't have volumes 28, 30, 32, 35 or 38
# (Turns out they are in the "Discoworld - Children's" (sub)series)
XXX__SeriesTitleDetails = namedtuple('SeriesTitleDetails',
                                'title_id, title, type, seriesnum, seriesnum_2')


class SeriesTitleDetails(object):
    def __init__(self, title_id, title, type,
                 seriesnum, seriesnum_2):
        self.title_id = title_id
        self.title = title
        self.type = type
        self.seriesnum = seriesnum
        self.seriesnum_2 = seriesnum_2

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
        return '#%s : %s (title_id=%d)' % (self.pretty_number, self.title,
                                           self.title_id)

# The downside of INCLUDE_ONLY_IF_ALL_UNNUMBERED is that (at least based on
# Hainish) it treats regular volumes the same as short stories, anthologies,
# omnibuses etc
class UnnumberedHandling(Enum):
    ALWAYS_INCLUDE = 1,
    ALWAYS_REJECT = 2,
    INCLUDE_ONLY_IF_ALL_UNNUMBERED = 3 # e.g. Hainish has no numbered volumes



def get_titles_for_series_id(conn, series,
                             ignore_unnumbered=UnnumberedHandling.ALWAYS_REJECT):
    """
    Given the name or ID of a series, return a list of SeriesTitleDetails

    series argument can be name or ID - determined by whether the argument is
    integer or not.
    ignore_unnumbered is an UnnumberedHandling value.

    TODO: optional filtering on pub type, which will mitigate some issues with
    INCLUDE_ONLY_IF_ALL_UNNUMBERED.

    """
    if isinstance(series, int):
        params = {'series_id': series}
        fltr = ['s.series_id = :series_id']
    else:
        params = {'series_title': series}
        fltr = ['s.series_title = :series_title']

    if ignore_unnumbered == UnnumberedHandling.ALWAYS_REJECT:
        fltr.append('title_seriesnum IS NOT NULL')
    fltrs = ' AND '.join(fltr)

    query = text("""SELECT title_id, title_title, title_ttype,
      title_seriesnum, title_seriesnum_2
    FROM titles t
    LEFT OUTER JOIN series s ON s.series_id = t.series_id
    WHERE %s
    ORDER BY title_seriesnum, title_seriesnum_2;""" % fltrs)

    results = conn.execute(query, **params).fetchall()
    titles = [SeriesTitleDetails(*z) for z in results]
    if ignore_unnumbered == UnnumberedHandling.INCLUDE_ONLY_IF_ALL_UNNUMBERED:
        titles_with_numbers = [z for z in titles if z.seriesnum is not None]
        if len(titles_with_numbers) != len(titles):
            return titles_with_numbers
    return titles

if __name__ == '__main__':
    conn = get_connection()

    try:
        # Let's hope there aren't any series whose name is just numbers...
        series = int(sys.argv[1])
    except ValueError:
        series = sys.argv[1]

    # data = get_titles_for_series_id(conn, 6, ignore_unnumbered=True) # Hyperion Cantos
    data = get_titles_for_series_id(conn, series)
    for i, item in enumerate(data, 1):
        print('%2d. %s' % (i, item))


