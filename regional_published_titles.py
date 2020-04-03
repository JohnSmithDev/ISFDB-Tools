#!/usr/bin/env python3
"""
Report on titles that have been published in one country/territory but
not another.
"""
from collections import Counter, OrderedDict
import pdb
import sys

from sqlalchemy.sql import text

from common import get_connection, parse_args, get_filters_and_params_from_args

# The values are string formats that need to be passed in the name of the
# price column - probably pub_price or p.pub_price.
# Keep these in alphabetic order
COUNTRY_PRICE_FILTERS = {
    'ca': "SUBSTRING(%s FROM  1 FOR 2) = 'C$'",
    'gb': "SUBSTRING(%s FROM  1 FOR 1) = '£'", # TODO: pre-decimalization support
    'us': "SUBSTRING(%s FROM  1 FOR 1) = '$'"
}

# Potentially NONFICTION also?  But could cover book intros etc?
RELEVANT_TITLE_TYPES = ('NOVEL', 'ANTHOLOGY', 'COLLECTION', 'OMNIBUS', 'CHAPBOOK')

RELEVANT_PUB_TYPES = ('hc', 'tp', 'pb', 'ebook')

def get_titles_published_in_country(conn, args, other_country=None):
    # TODO: This needs to handle variant titles e.g.
    # http://www.isfdb.org/cgi-bin/title.cgi?2507958 (2018 UK "Thirteen") is same as
    # http://www.isfdb.org/cgi-bin/title.cgi?186453 (2007 UK "Blank Man")
    # Not sure why we need 2 "Thirteen"s though:
    # http://www.isfdb.org/cgi-bin/title.cgi?223581 (unless it's for the "K."?

    initial_filter, params = get_filters_and_params_from_args(
        args, column_name_mappings={'year': 't.title_copyright'})

    filters = []
    if initial_filter:
        filters.append(initial_filter)

    if other_country:
        raw_filter = COUNTRY_PRICE_FILTERS[other_country.lower()]
        filters.append(raw_filter % 'p.pub_price')
    else:
        for country_code in args.countries:
            raw_filter = COUNTRY_PRICE_FILTERS[country_code.lower()]
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
        raise Exception('get_titles_published_in_country(): Must have some filters defined')

    query = text("""select t.title_id, t.title_title, t.title_copyright,
 t.title_ttype, t.title_language,
p.pub_id, p.pub_title, p.pub_year, p.publisher_id,
    p.pub_ptype, p.pub_ctype, p.pub_isbn, p.pub_price
 from titles t
LEFT OUTER JOIN pub_content pc ON pc.title_id = t.title_id
LEFT OUTER JOIN pubs p ON pc.pub_id = p.pub_id
WHERE %s
    ORDER BY t.title_ttype, p.pub_year, t.title_copyright;""" % (filter_string))


# substring(pub_price from  1 for 1) = '£'
# AND title_copyright > '2018-12-31';""")


    results = conn.execute(query, params)
    return results


if __name__ == '__main__':

    # TODO: two different country args, with appropriate help text to clarify
    #       which is which

    args = parse_args(sys.argv[1:],
                      description='Report on titles published in one territory but not another',
                      supported_args='ky')
    # pdb.set_trace()

    conn = get_connection()

    results1 = get_titles_published_in_country(conn, args)
    results2 = get_titles_published_in_country(conn, args, other_country='us')

    # This dictification will collapse titles published in multiple formats
    title_map_1 = OrderedDict((z.title_id, z) for z in results1)
    title_map_2 = dict((z.title_id, z) for z in results2)

    in_1_but_not_2 = set(title_map_1).difference(title_map_2)

    i = 1
    # Go through title_map_1 rather than in_1_but_not_2 to preserve ordering
    # from the SQL query
    for title_id, book in title_map_1.items():
        if title_id in in_1_but_not_2:
            print(i, book)
            i += 1




