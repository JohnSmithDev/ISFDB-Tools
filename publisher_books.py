#!/usr/bin/env python3
"""
Show what books a publisher published, optionally over a year range
"""

from collections import namedtuple
from datetime import timedelta, date
import json
from os.path import basename
import pdb
import sys

from sqlalchemy.sql import text

from common import get_connection, parse_args, get_filters_and_params_from_args
from country_related import derive_country_from_price
from utils import convert_dateish_to_date, pretty_list

OLD_BOOK_INTERVAL = timedelta(days=365*2)

ZERO_DAY = date(1,1,1)
def none_tolerant_date_sort_key(dt):
    """Stop max(), sorted() etc blowing up if a set of date values includes None"""
    if not dt:
        return ZERO_DAY
    return dt

class InvalidCountryError(Exception):
    pass


class Publication(object):
    def __init__(self, value_dict, valid_countries=None, reference=None):
        self.reference = reference
        self.pub_id = value_dict['pub_id']
        self.publication_date = convert_dateish_to_date(value_dict['pub_dateish'])
        self.format = value_dict['pub_ptype']
        self.price = value_dict['pub_price']
        if valid_countries:
            if self.country and self.country not in valid_countries:
                raise InvalidCountryError('Price %s is not valid for country %s' %
                                          (self.price, valid_countries))

    @property
    def country(self):
        return derive_country_from_price(self.price, self.reference)

    def __repr__(self):
        return '%s for %s on %s' % \
            (self.format, self.price or '<unknown price>', self.publication_date)


class CountrySpecificBook(object):
    def __init__(self, value_dict, valid_countries=None):
        self.publisher = value_dict['publisher_name']
        # set is used for authors to avoid stuff like Ken MacLeod being added
        # 3 times for The Corporration Wars Trilogy
        self.authors = set([value_dict['author_canonical']])
        self.title = value_dict['pub_title']
        self.title_id = value_dict['title_id']
        self.copyright_date = convert_dateish_to_date(value_dict['copyright_dateish'])
        self.publication_type = value_dict['title_ttype']

        publication = Publication(value_dict, valid_countries, reference=self.title)
        self.publications = [publication]

        self.valid_countries = valid_countries

    def add_coauthor(self, coauthor):
        self.authors.add(coauthor)

    def add_publication(self, value_dict):
        publication = Publication(value_dict, self.valid_countries,
                                  reference=self.title)
        self.publications.append(publication)

    @property
    def publication_ids(self):
        return [z.pub_id for z in self.publications]

    def add_variant(self, value_dict):
        # This blind calling of add_coauthor depends on its use of set() to
        # avoid dupes
        self.add_coauthor(value_dict['author_canonical'])

        # Maybe this should use sets too?  Or hash magic?
        if value_dict['pub_id'] not in self.publication_ids:
            self.add_publication(value_dict)

    def __repr__(self):
        newest_pub_date = max([z.publication_date for z in self.publications],
                              key=none_tolerant_date_sort_key)
        if newest_pub_date - self.copyright_date > OLD_BOOK_INTERVAL:
            extra_bit = ' (original copyright date %s)' % (self.copyright_date)
        else:
            extra_bit = ''
        pubs = '; '.join(str(z) for z in self.publications)
        return '%s published %s %s by %s in %s%s' % \
            (self.publisher, self.publication_type.lower(), self.title,
             # ', '.join(self.authors),
             pretty_list(list(self.authors), 2, 'authors'),
             # self.format, self.price or '<unknown price>',
             # self.publication_date,
             pubs,
             extra_bit)


def get_publisher_books(conn, args, countries=None):
    fltr, params = get_filters_and_params_from_args(
        args, column_name_prefixes={'year': 'pub'})

    # Q: maybe this should also join tot titles via pc.title_id?
    # A: Yes, but not for that reason - we need it to exclude INTERIORART,
    #    COVERART etc.  Not quite sure how yet though

    # We include pubs.pub_id as that's (maybe) the easiest way to track
    # publications with multiple authors
    query = text("""SELECT publisher_name, author_canonical,
                           pub_title, pubs.pub_id,
                           title_title, t.title_id,
                           CAST(pub_year AS CHAR) pub_dateish,
                           CAST(title_copyright AS CHAR) copyright_dateish,
                           pub_ptype, pub_price,
                           title_ttype
      FROM publishers p
        LEFT OUTER JOIN pubs ON pubs.publisher_id = p.publisher_id
        LEFT OUTER JOIN pub_content pc ON pubs.pub_id = pc.pub_id
        LEFT OUTER JOIN canonical_author ca ON ca.title_id = pc.title_id
        LEFT OUTER JOIN authors a ON ca.author_id = a.author_id
        LEFT OUTER JOIN titles t on t.title_id = pc.title_id
      WHERE title_ttype in ('NOVEL', 'CHAPBOOK', 'ANTHOLOGY', 'COLLECTION')
        AND %s
      ORDER BY t.title_id, pub_dateish, pubs.pub_id""" % (fltr))

    #print(fltr)
    #print(params)
    #print(query)

    results = conn.execute(query, **params).fetchall()
    ret_list = []
    pubid_dict = {}
    titleid_dict = {}
    for row in results:
        pubid = row['pub_id']
        titleid = row['title_id']

        try:
            known_title = titleid_dict[titleid]
            try:
                known_title.add_variant(row)
            except InvalidCountryError as err:
                pass
        except KeyError:
            try:
                bk = CountrySpecificBook(row, valid_countries=countries)
                ret_list.append(bk)
                titleid_dict[titleid] = bk
            except InvalidCountryError as err:
                pass
    return ret_list


if __name__ == '__main__':
    # script_name = basename(sys.argv[0])

    args = parse_args(sys.argv[1:],
                      description='Show books published by a publisher',
                      supported_args='kpy')

    conn = get_connection()
    results = get_publisher_books(conn, args,
                                  countries=[z.upper() for z in args.countries])
    for i, bk in enumerate(results, 1):
        print('%3d. %s' % (i, bk))
