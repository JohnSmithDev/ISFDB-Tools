#!/usr/bin/env python3
"""
Report on whether there is any pattern to works that get nominated for awards
and their publication dates.

Based on the supposition that a book that's been out for several months is
likely to have built up a bigger audience than one released later.  (Numerous
caveats to this of course.)
"""


from __future__ import division

from collections import defaultdict
import logging
import pdb
import sys

from common import get_connection, parse_args, get_filters_and_params_from_args

from finalists import get_type_and_filter, get_finalists
# from author_country import get_author_country
from publication_history import get_publications
from title_related import get_all_related_title_ids


def find_earliest_pub_date(pubs, preferred_countries=None):
    if not preferred_countries:
        # preferred_countries = ['GB', 'US'] # TODO: this should be determined by award
        preferred_countries = ['US', 'GB'] # TODO: this should be determined by award

    earliest_so_far = None
    for country in preferred_countries:
        if country not in pubs:
            continue
        pub_dates = [z[1] for z in pubs[country] if z[1]]
        if pub_dates:
            return min(pub_dates)
    return None



if __name__ == '__main__':
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

    for finalist in award_results:
        if not finalist.author or not finalist.title:
            warn('No author and/or title for title "%s/%s" - ignoring' %
                 (finalist.title, finalist.author))
            continue

        title_id = finalist.title_id
        if not title_id:
            warn('Missing title_id for "%s/%s" - ignoring' %
                 (finalist.title, finalist.author))
            # TODO: some sort of lookup
            # Only known example so far is
            # "The Wheel of Time (series)/Robert Jordan+Brandon Sanderson"
            continue

        FIRST_ATTEMPT = """
        book_args = parse_args(['-A', finalist.author, '-T' , finalist.title],
                               description='whatever', supported_args='at')
        title_id = get_title_id(conn, book_args)
        if not title_id:
            warn('Could not find title_id for "%s/%s" - ignoring' %
                 (finalist.title, finalist.author))
            continue
        if len(title_id) > 1:
            warn('Multiple title_ids found for "%s/%s" (%s)- ignoring' %
                 (finalist.title, finalist.author, title_id))
            continue
        # print('%s / %s / %s' % (finalist.author, finalist.title, title_id))

        pubs = get_publications(conn, list(title_id.keys())[0])
        """
        title_ids = get_all_related_title_ids(conn, title_id)
        if not title_ids:
            logging.error('No title_ids found for %s' % (title_id))
            pdb.set_trace()
        pubs = get_publications(conn, title_ids)


        earliest_pub_date = find_earliest_pub_date(pubs)
        if not earliest_pub_date:
            warn('No pub dates found for "%s/%s" (title_id=%d)- ignoring' %
                 (finalist.title, finalist.author, title_id))
            continue

        # print(pub_dates)
        print('%s : %s - %s' % (earliest_pub_date, finalist.author, finalist.title))

