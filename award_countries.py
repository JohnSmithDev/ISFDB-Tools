#!/usr/bin/env python3

from __future__ import division

from collections import defaultdict, Counter
import json
import logging
import pdb
import re
import sys

from common import get_connection, parse_args, get_filters_and_params_from_args

from finalists import get_type_and_filter, get_finalists
from author_country import get_author_country

UNKNOWN_COUNTRY = '??'

MULTIPLE_AUTHORS_SEPARATOR = '+' # e.g. Brandon Sanderson + someone I think?
PSEUDONYM_SEPARATOR = '^' # e.g. Edmond Hamilton^Brett Sterling (Retro Hugo Novel 1946)

def get_award_countries(conn, args, level_filter):
    award_results = get_finalists(conn, args, level_filter)
    author_countries = {}
    country_counts = defaultdict(int)
    country_authors = defaultdict(list) # Ugh, too similar to author_countries - TODO: change
    overall_total = 0

    for row in award_results:
        if not row.author:
            logging.warning('No author for title "%s"' % (row.title))
            continue
        if PSEUDONYM_SEPARATOR in row.author:
            # We only want to use one of these
            real_name, pseudonum = row.author.split(PSEUDONYM_SEPARATOR)
            # For now assume the real name is right TODO: test both, and use the best
            authors = [real_name]
        else:
            authors = row.author.split('+')
        increment = 1 / len(authors)
        for author in authors:
            author_filter_args = parse_args(['-A', author],
                                        'whatever', supported_args='a')
            if author not in author_countries:
                val = get_author_country( conn, author_filter_args, overrides=True)
                if not val:
                    if args.verbose:
                        logging.warning('Country unknown for author "%s"' % (author))
                    val = UNKNOWN_COUNTRY
                # The author might be a pseudonym for one or more authors (e.g.
                # James S. A. Corey), hence the splitting.  This is separate from
                # open collaborations indicated by a + in the name, and handled
                # further up.
                author_countries[author] = val.split(',')

            acs = author_countries[author]
            for c in acs:
                country_counts[c] += increment / len(acs)
                country_authors[c].append(author)

            overall_total += increment

        # print('%d : %s %s' % (row.year, author_countries[row.author], row.author))

    return country_counts, country_authors, overall_total


if __name__ == '__main__':
    typestring, level_filter = get_type_and_filter('finalists')

    args = parse_args(sys.argv[1:],
                      description='Show %s for an award' % (typestring),
                      supported_args='cwy')

    conn = get_connection()
    country_counts, country_authors, overall_total = get_award_countries(
        conn, args, level_filter)

    for k, v in sorted(country_counts.items(), key=lambda z: z[1], reverse=True):
        # authors = country_authors[k]
        author_counts = Counter(country_authors[k])
        num_authors = len(author_counts)

        most_awarded = [z[0] for z in author_counts.most_common(2)]
        if num_authors == 1:
            a = most_awarded[0]
        elif num_authors == 2:
            a = '%s and %s' % (most_awarded[0], most_awarded[1])
        else:
            a = '%s, %s and %d others' % (most_awarded[0], most_awarded[1], num_authors-2)

        print('%s : %3d works (%2d%%), %3d authors - %s' % (k,
                                                            v, (100 * v / overall_total),
                                                            num_authors, a))
