#!/usr/bin/env python3

from __future__ import division

from collections import defaultdict
import logging
import pdb
import sys

from common import get_connection, parse_args, get_filters_and_params_from_args

from finalists import get_type_and_filter, get_finalists
from author_country import get_author_country

UNKNOWN_COUNTRY = '??'


if __name__ == '__main__':
    typestring, level_filter = get_type_and_filter('finalists')


    args = parse_args(sys.argv[1:],
                      description='Show %s for an award' % (typestring),
                      supported_args='cwy')

    conn = get_connection()
    award_results = get_finalists(conn, args, level_filter)
    author_countries = {}
    country_counts = defaultdict(int)
    overall_total = 0

    for row in award_results:
        if not row.author:
            logging.warning('No author for title "%s"' % (row.title))
            continue
        authors = row.author.split('+')
        increment = 1 / len(authors)
        for author in authors:
            author_filter_args = parse_args(['-A', author],
                                        'whatever', supported_args='a')
            if author not in author_countries:
                val = get_author_country( conn, author_filter_args)
                if not val:
                    if args.verbose:
                        logging.warning('Country unknown for author "%s"' % (author))
                    val = UNKNOWN_COUNTRY
                author_countries[author] = val

            country_counts[author_countries[author]] += increment
            overall_total += increment

        # print('%d : %s %s' % (row.year, author_countries[row.author], row.author))


    for k, v in sorted(country_counts.items(), key=lambda z: z[1], reverse=True):
        print('%s : %3d (%d%%)' % (k, v, (100 * v / overall_total)))
