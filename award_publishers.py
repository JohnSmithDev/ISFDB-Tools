#!/usr/bin/env python3
"""
Output stats regard who are the publishers of the finalists/nominees of an award
category
"""

from collections import namedtuple, Counter
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
from finalists import (get_finalists, get_type_and_filter)
from title_publications import (get_earliest_pub, NoPublicationsFoundError)
from title_related import get_all_related_title_ids # This doesn't handle language

if __name__ == '__main__':
    typestring, level_filter = get_type_and_filter('finalists')


    parser = create_parser(description='Show %s for an award' % (typestring),
                           supported_args='cwy')
    NOPE = """
    parser.add_argument('-k', dest='csv_file', nargs='?',
                        help='Output as CSV to named file, no header row'
                        '(default is human-readable output)')
    parser.add_argument('-K', dest='csv_file_with_header', nargs='?',
                        help='Output as CSV to named file, with header row'
                        '(default is human-readable output)')
    """
    args = parse_args(sys.argv[1:], parser=parser)

    conn = get_connection()
    level_filter = ''
    award_results = get_finalists(conn, args, level_filter)

    venue_counts = Counter()
    format_counts = Counter()

    for row in award_results:
        # We specify only_same_types=False to catch stuff published in serial
        # form only e.g. title_id=1243403
        # However we don't want translations
        all_title_ids = get_all_related_title_ids(conn, row.title_id,
                                                  only_same_types=False,
                                                  only_same_languages=True)
        try:
            earliest_pub = get_earliest_pub(conn, all_title_ids)
            venue = earliest_pub['publisher_name']
            fmt = earliest_pub['pub_ctype'].lower()
        except NoPublicationsFoundError as err:
            venue = 'unknown'
            fmt = 'unknown'
        # print(earliest_pub)
        print('%s / %s (%s)' % (row, venue, fmt))

        venue_counts[venue] += 1
        format_counts[fmt] += 1


    # format counts only makes sense for novel really
    for c in (venue_counts, format_counts):
        print()
        for i, (k, v) in enumerate(c.most_common(), 1):
            print('%2d. %-50s : %2d' % (i, k, v))
