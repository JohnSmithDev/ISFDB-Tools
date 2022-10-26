#!/usr/bin/env python3
"""
Output stats regard who are the publishers of the finalists/nominees of an award
category
"""

from collections import Counter
import pdb
import sys

from common import (get_connection, parse_args, get_filters_and_params_from_args,
                    create_parser)
# from isfdb_utils import pretty_nth
# from award_related import (BOGUS_AUTHOR_NAMES, DODGY_TITLES_AND_PSEUDO_AUTHORS,
#                            EXCLUDED_AUTHORS,
#                           load_category_groupings)
from finalists import (get_finalists, get_type_and_filter)
from title_publications import (get_earliest_pub, NoPublicationsFoundError)
from title_related import get_all_related_title_ids # This doesn't handle language
from publisher_variants import REVERSE_PUBLISHER_VARIANTS


def process_finalists(conn, award_results, only_from_country=None,
                      output_function=print):
    """
    Process and output stats from a raw list/iterable of award finalists
    """
    venue_counts = Counter()
    sanitised_publisher_counts = Counter()
    format_counts = Counter()

    for row in award_results:
        # We specify only_same_types=False to catch stuff published in serial
        # form only e.g. title_id=1243403
        # However we don't want translations
        all_title_ids = get_all_related_title_ids(conn, row.title_id,
                                                  only_same_types=False,
                                                  only_same_languages=True)
        try:
            earliest_pub = get_earliest_pub(conn, all_title_ids,
                                            only_from_country=only_from_country)
            venue = earliest_pub['publisher_name']
            fmt = earliest_pub['pub_ctype'].lower()
        except NoPublicationsFoundError:
            venue = 'unknown'
            fmt = 'unknown'
        publisher = REVERSE_PUBLISHER_VARIANTS.get(venue, venue)
        output_function('%s / %s (%s)' % (row, venue, fmt))

        venue_counts[venue] += 1
        sanitised_publisher_counts[publisher] += 1
        format_counts[fmt] += 1


    # format counts only makes sense for novel really
    for label, c in (('Unsanitised publisher', venue_counts),
                     ('Publisher', sanitised_publisher_counts),
                     ('Format', format_counts)):
        output_function(f'= {label} =')
        for i, (k, v) in enumerate(c.most_common(), 1):
            output_function('%2d. %-50s : %2d' % (i, k, v))
        output_function()

if __name__ == '__main__':
    typestring, level_filter = get_type_and_filter('finalists')

    parser = create_parser(description='Show %s for an award' % (typestring),
                           supported_args='ckwy')

    args = parse_args(sys.argv[1:], parser=parser)

    mconn = get_connection()
    level_filter = ''
    results = get_finalists(mconn, args, level_filter)

    if args.countries:
        country = args.countries[0]
    else:
        country = None
    process_finalists(mconn, results, only_from_country=country)
