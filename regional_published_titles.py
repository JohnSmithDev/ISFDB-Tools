#!/usr/bin/env python3
"""
Report on titles that have been published in one country/territory but
not another.
"""
from collections import OrderedDict
import os
import pdb
import re
import sys

from sqlalchemy.sql import text

from common import get_connection, parse_args, get_filters_and_params_from_args
from isfdb_utils import convert_dateish_to_date

class ArgumentError(Exception): # I thought there was a built-in for this?
    pass

# The values are string formats that need to be passed in the name of the
# price column - probably pub_price or p.pub_price.
# Keep these in alphabetic order
# GB filter shoould really also check for prices ending in 'p' (i.e. less than
# one pound) but as of 2020-04-04, there are only 13 of these in total in the DB.
COUNTRY_PRICE_FILTERS = {
    'au': "SUBSTRING(%s FROM  1 FOR 2) = 'A$'",
    'ca': "SUBSTRING(%s FROM  1 FOR 2) = 'C$'",
    'gb': "SUBSTRING(%s FROM  1 FOR 1) = '£'", # TODO: pre-decimalization support (if possible?)
    'us': "SUBSTRING(%s FROM  1 FOR 1) = '$'"
}

# Potentially NONFICTION also?  But could cover book intros etc?
RELEVANT_TITLE_TYPES = ('NOVEL', 'ANTHOLOGY', 'COLLECTION', 'OMNIBUS', 'CHAPBOOK')

RELEVANT_PUB_TYPES = ('hc', 'tp', 'pb', 'ebook')

def get_titles_published_in_country(conn, country, year=None):
    # Don't want to use args/get_filters_and_params_from-args(), because this
    # will be run multiple times, sometimes with different values from what
    # the args indicate.

    filters = []
    params = {}

    if year:
        filters.append('YEAR(t.title_copyright) = :year')
        params = {'year': year}

    if country:
        raw_filter = COUNTRY_PRICE_FILTERS[country.lower()]
        filters.append(raw_filter % 'p.pub_price')

    filters.append('t.title_ttype IN :title_types')
    params['title_types'] = RELEVANT_TITLE_TYPES

    filters.append('p.pub_ptype IN :pub_types')
    params['pub_types'] = RELEVANT_PUB_TYPES

    filters.append("t.title_non_genre = 'No'")
    filters.append("t.title_graphic = 'No'")
    filters.append("t.title_jvn = 'No'")

    if filters:
        filter_string = ' AND '.join(filters)
    else:
        raise ArgumentError('get_titles_published_in_country(): Must have some filters defined')

    query = text("""SELECT t.title_id, t.title_title title, t.title_parent,
    t.series_id, s.series_title series,
CAST(t.title_copyright AS CHAR) first_pub_date,
 t.title_ttype, t.title_language,
    a.author_id, a.author_canonical author, a.author_lastname,
p.pub_id, p.pub_title,
CAST(p.pub_year AS CHAR) pub_date, p.publisher_id,
    p.pub_ptype, p.pub_ctype, p.pub_isbn, p.pub_price
 FROM titles t
LEFT OUTER JOIN series s on s.series_id = t.series_id
LEFT OUTER JOIN pub_content pc ON pc.title_id = t.title_id
LEFT OUTER JOIN pubs p ON pc.pub_id = p.pub_id
LEFT OUTER JOIN canonical_author ca ON ca.title_id = t.title_id
LEFT OUTER JOIN authors a ON a.author_id = ca.author_id
WHERE %s
    ORDER BY a.author_lastname, a.author_legalname, a.author_canonical, t.title_title;""" % (filter_string))
#     ORDER BY t.title_ttype, p.pub_year, t.title_copyright;""" % (filter_string))

    # print(query)

    results = conn.execute(query, params)
    return results


def get_titles_published_in_one_country_only(conn, country, other_country, year,
                                             other_country_data=None,
                                             output_function=print):
    """
    Return a tuple of three items:
    * An OrderedDict mapping title_id to title/pub/etc details of all books
      published in country in the specified year
    * The set of those title_ids that were not published in other_country
    * A dict mapping title_id to title/pub etc details for all books *ever*
      published in other_country.  Because this is computationally expensive
      to generate, it is returned as a convenience for any subsequent iterations
      to re-use.
    """

    if not other_country_data:
        # Note lack of any year filter on the other one, we don't want false
        # positives due to titles being published in different years.
        # This will obviously be resource intensive :-(
        results_other = get_titles_published_in_country(conn, other_country)
        # This one doesn't get collapsed, as we want it to be as comprehensive as
        # possible.  TODO (maybe): have both title_parent and title_id as keys,
        # although I *think* this is overkill
        other_country_data = dict((z.title_parent or z.title_id, z) for z in results_other)

    results1 = get_titles_published_in_country(conn, country, year)
    # This dictification will collapse titles published in multiple formats
    title_map_1 = OrderedDict((z.title_parent or z.title_id, z) for z in results1)


    in_1_but_not_2 = set(title_map_1).difference(other_country_data)
    output_function('%d titles in %s set for %d, %d titles in %s set, %d titles in first but not second' %
                    (len(title_map_1), country.upper(), year,
                     len(other_country_data), other_country.upper(),
                     len(in_1_but_not_2)))

    return (title_map_1, in_1_but_not_2, other_country_data)

if __name__ == '__main__':

    # TODO: two different country args, with appropriate help text to clarify
    #       which is which

    args = parse_args(sys.argv[1:],
                      description='Report on titles published in one territory but not another',
                      supported_args='ky')

    conn = get_connection()

    if len(args.countries) > 2:
        raise ArgumentError('Cannot handle more than two country arguments')

    country = args.countries[0]
    if len(args.countries) == 1:
        if country.lower() == 'us':
           other_country = 'gb'
        else:
            other_country = 'us'
    else:
        other_country = args.countries[1]

    if '-' in args.year:
        from_year, to_year = [int(z) for z in args.year.split('-')]
        years = range(from_year, to_year + 1)
    elif ',' in args.year:
        years = [int(z) for z in args.year.split(',')]
    else:
        years = [int(args.year)]

    results_other = None
    for year in years:
        title_map_1, in_1_but_not_2, results_other = get_titles_published_in_one_country_only(
            conn, country, other_country, year,
            other_country_data=results_other)
        # pdb.set_trace()

        i = 1
        # Go through title_map_1 rather than in_1_but_not_2 to preserve ordering
        # from the SQL query
        for title_id, book in title_map_1.items():
            if title_id in in_1_but_not_2:
                print(year, i, book)
                #pdb.set_trace()
                i += 1




