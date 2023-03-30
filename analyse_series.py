#!/usr/bin/env python3
"""
Wrapper for analyse_anthology.py to process all the titles in a series

Useful series IDs:

* 23931 - Strahan Best SF & F 2007-2019
* 8258 - Dozois Best SF 1984-2019
* 11537 - Datlow & Windling Best Fantasy & Horror 1989-2008
* 27939 - Horton Best SF & F 2010-2022
* 40163 - Best American SF & F 2015-2022
* 42005 - Clarke Best SF 2016-2023
* 8383 - Hartwell Year's Best SF 1996-2013
"""


import pdb
import sys

from sqlalchemy.sql import text

from common import get_connection

from analyse_anthology import analyse_title

def get_series_entries(conn, series_id, exclude_children=True):
    """
    Return a list of title IDs, names etc for the specified series
    """
    query = text("""SELECT title_id, title_title, YEAR(title_copyright) year,
    title_seriesnum, title_parent
    FROM titles
    WHERE series_id = :series_id
    ORDER BY title_seriesnum;""")

    results = conn.execute(query, {'series_id': series_id}).fetchall()

    if exclude_children:
        results = [z for z in results if z['title_parent'] == 0]
    return results


def title_heading(t):
    """
    Given a dict with values derived from the titles table, return a readable string of
    them (__repr__ style)
    """
    bits = []
    if t['title_seriesnum'] is not None:
        bits.append('#' + t['title_seriesnum'])
    bits.extend((t['title_title'],
                 '[%d]' % t['year'],
                 '(title_id=%d)' %  t['title_id']
                 ))
    return ' '.join(bits)


if __name__ == '__main__':
    conn = get_connection()

    series_id = int(sys.argv[1])

    for i, t in enumerate(get_series_entries(conn, series_id)):
        if i > 0:
            print()
        print('= %s =\n' % title_heading(t))
        analyse_title(conn, t['title_id'])
