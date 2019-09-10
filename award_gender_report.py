#!/usr/bin/env python3
"""
Initially, this is a hacky script to pull in a bunch of authors and (try to)
get their gender from Wikipedia.

As that stands, it's not particularly interesting or useful - it's mainly for me
to test the download throttling and to see what proportion of Wiki pages have
categories we can use.
"""

from __future__ import division

from collections import defaultdict, Counter
import logging
import pdb
import sys

from common import (get_connection, parse_args, get_filters_and_params_from_args,
                    AmbiguousArgumentsError)

from finalists import get_type_and_filter, get_finalists
# from publication_history import get_publications_by_country
# from title_related import get_all_related_title_ids
# from award_related import extract_authors_from_author_field
from gender_analysis import (analyse_authors_by_gender, report_gender_analysis,
                             year_data_as_cells)



if __name__ == '__main__':
    # logging.getLogger().setLevel(logging.DEBUG)
    typestring, level_filter = get_type_and_filter('finalists')

    args = parse_args(sys.argv[1:],
                      description='Compare award nominations to publication dates',
                      supported_args='cwyv')
    if not args.award and not args.exact_award:
        raise Exception('Must specify an award (-w or -W)')

    def warn(txt):
        if args.verbose:
            logging.warning(txt)

    conn = get_connection()
    award_results = get_finalists(conn, args, level_filter)

    stats = analyse_authors_by_gender(conn, award_results)
    report_gender_analysis(*stats)

    year_data = year_data_as_cells(stats[2], output_function=print)
    # for row in year_data:
    #    print(','.join([str(z) for z in row]))
