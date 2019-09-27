#!/usr/bin/env python3
"""
Report on the proportion of novels that are serialized vs standalone, grouped
by copyright date.

See also http://www.isfdb.org/cgi-bin/stats.cgi?8 , which should match
fairly closely, albeit showing slightly different metrics.

"""


from collections import defaultdict
from datetime import datetime
# from functools import reduce, lru_cache
import pdb
import sys

from sqlalchemy.sql import text

from common import (get_connection, parse_args, AmbiguousArgumentsError)

def get_stats(conn, min_year=0, max_year=2999, language_filter=17):
    """
    Return (a generator, I think) of rows of (year, volume_group, count)

    language_filter is numeric language code, 17=English
    """
    filters = []
    if language_filter:
        filters.append(' title_language = %d ' % (language_filter))
    if filters:
        filter_text = ' AND ' + (' AND '.join(filters))
    else:
        filter_text = ''

    query = text('''SELECT year,
       CASE
         WHEN NOT book_in_a_series THEN 'Completely standalone'
         WHEN volume_number = 'Unnumbered' THEN 'Series, unnumbered'
         ELSE CONCAT('Series, ', volume_number)
       END series_vol,
    count(1) c
     FROM (
        SELECT YEAR(title_copyright) year, (series_id IS NOT NULL) book_in_a_series,
          -- LEAST(title_seriesnum, 20) volume_number
          CASE
            WHEN title_seriesnum >= 20 THEN 'Vols 20+'
            WHEN title_seriesnum >= 10 THEN 'Vols 10-19'
            WHEN title_seriesnum >= 6  THEN 'Vols 06-09'
            WHEN title_seriesnum IS NULL THEN 'Unnumbered'
            ELSE CONCAT('Vol ', LPAD(title_seriesnum, 2, '0'))
          END volume_number
        FROM titles
        WHERE title_ttype = 'NOVEL' AND title_non_genre = 'No' AND
          title_graphic = 'No' %s
     ) annual_novels
     WHERE year >= :min_year AND year <= :max_year
     GROUP BY year, series_vol
     ORDER BY year, series_vol;''' % (filter_text))

    rows = conn.execute(query, {'min_year': min_year, 'max_year': max_year})
    return rows

def turn_raw_stats_into_cells(rows):
    """
    Turn the output from get_stats() into a form more suitable for Excel/Google
    Sheets/CSVWriter use.

    Yields an iterable of lists, the first list are table headers, the following are
    year and relevant values.  Years are not guaranteed to be consecutive, but
    "columns" will have zeroes inserted to keep them constant and matching the
    headers.
    """

    vols = set()
    years = set()
    year_and_vol_to_count = defaultdict(int)
    for y, v, c in rows:
        vols.add(v)
        years.add(y)
        year_and_vol_to_count[(y, v)] = c

    sorted_vols = sorted(vols, key=lambda z: z.lower())
    headings = ['Year']
    headings.extend(sorted_vols)
    yield headings

    for y in sorted(years):
        row = [y]
        row.extend([year_and_vol_to_count[y, vol] for vol in sorted_vols])
        yield row




if __name__ == '__main__':
    conn = get_connection()
    rows = get_stats(conn, min_year=1900, max_year=datetime.today().year)

    for cell_row in turn_raw_stats_into_cells(rows):
        print(cell_row)


