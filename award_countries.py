#!/usr/bin/env python3

from __future__ import division

from collections import defaultdict, Counter
import json
import logging
import pdb
import re
import sys

from common import get_connection, parse_args, get_filters_and_params_from_args
from utils import pretty_list, padded_plural
from finalists import get_type_and_filter, get_finalists
from author_country import get_author_country
from award_related import (extract_authors_from_author_field,
                           sanitise_authors_for_dodgy_titles)

UNKNOWN_COUNTRY = '??'

MULTIPLE_AUTHORS_SEPARATOR = '+' # e.g. Brandon Sanderson + someone I think?
PSEUDONYM_SEPARATOR = '^' # e.g. Edmond Hamilton^Brett Sterling (Retro Hugo Novel 1946)

XXX_BOGUS_AUTHOR_NAMES = ('', '********')

XXX_DODGY_TITLES_AND_PSEUDO_AUTHORS = {
    'No Award': 'Noah Ward'
}

# This is a nasty hack for pseudonyms, TODO: think how to do it better
XXX_DONT_USE_THESE_REAL_NAMES = (
    'Compton Crook',
)

# TODO: Add argument to override MAX_AUTHORS
MAX_AUTHORS = 3
# MAX_AUTHORS = 10

# TODO: make this configurable via command-line argument
EXCLUDED_AUTHORS = set(['Noah Ward'])

def xxx_extract_authors_from_author_field(raw_txt):
    txt = raw_txt.strip()
    if txt.startswith('(') and txt.endswith(')'): # "(Henry Kuttner+C. L. Moore)" - but see below
        txt = txt[1:-1].strip()
    if PSEUDONYM_SEPARATOR in txt:
        # We only want to use one of these
        real_name, pseudonym = txt.split(PSEUDONYM_SEPARATOR)
        # For now assume the real name is right TODO: test both, and use the best
        # UPDATE: That assumption turned out to be wrong for "Compton Crook^Stephen Tall"

        # Note that we can have both separators e.g.
        # '(Henry Kuttner+C. L. Moore)^Lewis Padgett' hence the recursion
        if real_name in DONT_USE_THESE_REAL_NAMES:
            return extract_authors_from_author_field(pseudonym)
        else:
            return extract_authors_from_author_field(real_name)
    else:
        authors = txt.split(MULTIPLE_AUTHORS_SEPARATOR)
    return [z.strip() for z in authors] # extra strip just to be super-sure

def xxx_replace_name_if_necessary(title, author):
    if title in DODGY_TITLES_AND_PSEUDO_AUTHORS and author in BOGUS_AUTHOR_NAMES:
        return DODGY_TITLES_AND_PSEUDO_AUTHORS[title]
    else:
        return author


def get_award_countries(conn, args, level_filter):
    # pdb.set_trace()
    award_results = get_finalists(conn, args, level_filter)
    author_countries = {}
    country_counts = defaultdict(int)
    country_authors = defaultdict(list) # Ugh, too similar to author_countries - TODO: change
    overall_total = 0

    for row in award_results:
        authors = extract_authors_from_author_field(row.author)

        if not authors or len(authors) == 0:
            logging.warning('No author for title "%s"' % (row.title))
            continue
        # print(authors, row.title)
        authors = sanitise_authors_for_dodgy_titles(row.title, authors)
        REPLACED_BY_ABOVE_LINE = """
        if row.title in DODGY_TITLES_AND_PSEUDO_AUTHORS:
            replacement = DODGY_TITLES_AND_PSEUDO_AUTHORS[row.title]
            authors = [replace_author_name_if_necessary(row.title, z) for z in authors]
        """
        if '' in authors:
            logging.warning('Empty author for title "%s"' % (row.title))

        if set(authors) & EXCLUDED_AUTHORS:
            logging.debug('Ignoring book %s with excluded author(s) %s' %
                          (row.title, authors))
            continue

        # print(authors)
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

    for k, num_works in sorted(country_counts.items(), key=lambda z: z[1], reverse=True):
        # authors = country_authors[k]
        author_counts = Counter(country_authors[k])
        num_authors = len(author_counts)
        # pdb.set_trace()

        ordered_authors = [z[0] for z in author_counts.most_common()]
        a = pretty_list(ordered_authors, max_items=MAX_AUTHORS, others_label='author/authors')

        print('%s : %s (%2d%%), %s - %s' % (k,
                                            padded_plural(num_works, 'work', number_length=3),
                                            (100 * num_works / overall_total),
                                            padded_plural(num_authors, 'author', number_length=3),
                                            a))
