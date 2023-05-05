#!/usr/bin/env python3
"""
Show what books a publisher published, optionally over a year range.

This is intended for both standalone use and as a library module for use in
more complicated scripts/reports/whatever.

Example usage:

  ./debut_novel_stats.py -P Gollancz -PP -n NOVEL -y 2020- -d -D

"""

# from collections import namedtuple
from datetime import timedelta, date
from functools import lru_cache
# import json
import logging
# from os.path import basename
import pdb
import sys

from sqlalchemy.sql import text


from common import (get_connection,
                    parse_args, create_parser, get_filters_and_params_from_args)
from country_related import derive_country_from_price
from isfdb_utils import convert_dateish_to_date, pretty_list
from magazine_reviews import normalize_month

ZERO_DAY = date(1,1,1)

OLD_BOOK_INTERVAL = timedelta(days=365*2)

# See comment in docstring for get_publisher_books() about what values are
# supported
DEFAULT_BOOK_TYPES = ('NOVEL', 'CHAPBOOK', 'ANTHOLOGY', 'COLLECTION')



def none_tolerant_date_sort_key(dt):
    """Stop max(), sorted() etc blowing up if a set of date values includes None"""
    if not dt:
        return ZERO_DAY
    return dt

def are_dates_consistent(this_date, other_date):
    """
    Return True iff this_date is reasonably close to earlier_date - by
    default within a year.  (Returns False if either dates are unknown or vague)

    Currently this functionality is not (meaningfully) used, and perhaps the
    logic needs tweaking.
    """

    if not this_date or not other_date:
        return False
    if this_date.year in (0, 8888) or other_date.year in (0, 8888):
        return False

    if this_date.year == other_date.year:
        return True
    else:
        return False


class InvalidCountryError(Exception):
    pass


class Publication(object):
    def __init__(self, value_dict, valid_countries=None, reference=None):
        self.reference = reference
        self.pub_id = value_dict['pub_id']
        self.publication_date = convert_dateish_to_date(value_dict['pub_dateish'])
        self.format = value_dict['pub_ptype']
        self.price = value_dict['pub_price']
        self.isbn = value_dict['pub_isbn']
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
    def __init__(self, value_dict, valid_countries=None, conn=None):
        self.publisher = value_dict['publisher_name']
        # set is used for authors to avoid stuff like Ken MacLeod being added
        # 3 times for The Corporration Wars Trilogy
        self.authors = set([value_dict['author_canonical']])
        self.author_ids = set([value_dict['author_id']])
        # author_id_to_name should supercede .authors and .author_ids (probably
        # with properties to cover any code that used them
        self.author_id_to_name = {value_dict['author_id']: value_dict['author_canonical']}
        self.title = value_dict['pub_title']
        self.title_id = value_dict['title_id']
        self.title_parent = value_dict['title_parent']
        self.title_language = value_dict['title_language']
        self.copyright_date = convert_dateish_to_date(value_dict['copyright_dateish'])
        if self.title_parent and conn:
            self.best_copyright_date = self._get_best_copyright_date(conn)
        else:
            self.best_copyright_date = self.copyright_date

        self.publication_type = value_dict['title_ttype']

        publication = Publication(value_dict, valid_countries, reference=self.title)
        self.publications = [publication]

        self.valid_countries = valid_countries

    def add_coauthor(self, coauthor, coauthor_id):
        self.authors.add(coauthor)
        self.author_ids.add(coauthor_id)
        self.author_id_to_name[coauthor_id] = coauthor

    def add_publication(self, value_dict):
        publication = Publication(value_dict, self.valid_countries,
                                  reference=self.title)
        self.publications.append(publication)


    @lru_cache()
    def _get_best_copyright_date(self, conn):
        """
        The .copyright_date value will return the date of the title, but the title
        might be a child of an older parent - use this to ensure that
        the latter is checked, at the (possible) expense of extra database load.
        """
        if not self.title_parent:
            return self.copyright_date
        query = text("""SELECT title_title, CAST(title_copyright AS CHAR) copyright_dateish
        FROM titles WHERE title_id = :title_parent AND title_language = :language;""")
        results = conn.execute(query, {'title_parent': self.title_parent,
                                       'language': self.title_language}).fetchall()

        if not results:
            # Hopefully this is due to language mismatch
            return self.copyright_date
        stuff = results[0]
        cdt = convert_dateish_to_date(stuff.copyright_dateish)
        if are_dates_consistent(cdt, self.copyright_date):
            THIS_IS_TOO_NOISY = """
            logging.warning('Copyright year inconsistency for %d/%s vs %d/%s : %d != %d' %
                            (self.title_id, self.title,
                             self.title_parent, stuff.title_title,
                             self.copyright_date.year, cdt.year))
            """
            pass

        return cdt or self.copyright_date

    @property
    def publication_ids(self):
        return [z.pub_id for z in self.publications]

    def add_variant(self, value_dict):
        # This blind calling of add_coauthor depends on its use of set() to
        # avoid dupes
        self.add_coauthor(value_dict['author_canonical'], value_dict['author_id'])

        # Maybe this should use sets too?  Or hash magic?
        if value_dict['pub_id'] not in self.publication_ids:
            self.add_publication(value_dict)


    @property
    def first_publication(self):
        pub_dates = [z.publication_date for z in self.publications
                         if z.publication_date is not None]
        if pub_dates:
            return min(pub_dates)
        else:
            # e.g. http://www.isfdb.org/cgi-bin/pl.cgi?286626
            return None

    # These next few are to make life easy for my SVG charting code, you
    # probably shouldn't use them in most other circumstances
    @property
    def author(self):
        return '+'.join(self.authors)
    @property
    def year(self):
        try:
            return self.first_publication.year
        except AttributeError: # if first_publication == None
            return None
    @property
    def month(self):
        # Q: does this need protecting against first_publication == None?
        return normalize_month(self.first_publication)

    def __repr__(self):
        newest_pub_date = max([z.publication_date for z in self.publications],
                              key=none_tolerant_date_sort_key)
        if newest_pub_date and self.copyright_date and \
           (newest_pub_date - self.copyright_date > OLD_BOOK_INTERVAL):
            extra_bit = ' (original copyright date %s)' % (self.copyright_date)
        else:
            extra_bit = ''
        pubs = '; '.join(str(z) for z in self.publications)
        return '%s published %s %s by %s in %s%s' % \
            (self.publisher, self.publication_type.lower(),
             self.title,
             # self.title_id, self.publication_ids,
             # ', '.join(self.authors),
             pretty_list(list(self.authors), 2, 'authors'),
             # self.format, self.price or '<unknown price>',
             # self.publication_date,
             pubs,
             extra_bit)



def get_publisher_books(conn, args, countries=None, original_adult_genre_only=True,
                        book_types=DEFAULT_BOOK_TYPES):
    """
    Note that book_types is (effectively) checked against both title_ttype and
    pub_ctype, but there are some values that are valid in one but not the other.
    The common ones are: 'ANTHOLOGY', 'COLLECTION', 'NONFICTION', 'NOVEL',
    'OMNIBUS' and 'CHAPBOOK'.
    """
    fltr, params = get_filters_and_params_from_args(
        args, column_name_mappings={'year': 'pub_year'})

    if original_adult_genre_only:
        fltr += " AND title_non_genre = 'No' AND title_graphic = 'No' " + \
                " AND title_nvz = 'No' AND title_jvn = 'No'"

    params['book_types'] = book_types

    # Q: maybe this should also join tot titles via pc.title_id?
    # A: Yes, but not for that reason - we need it to exclude INTERIORART,
    #    COVERART etc.  Not quite sure how yet though

    # We include pubs.pub_id as that's (maybe) the easiest way to track
    # publications with multiple authors
    query = text("""SELECT publisher_name,
                           a.author_id, author_canonical,
                           pub_title, pubs.pub_id,
                           title_title, t.title_id, t.title_parent,
                           t.title_language,
                           CAST(pub_year AS CHAR) pub_dateish,
                           CAST(title_copyright AS CHAR) copyright_dateish,
                           pub_ptype, pub_price, pub_isbn,
                           title_ttype, pub_ctype
      FROM publishers p
        LEFT OUTER JOIN pubs ON pubs.publisher_id = p.publisher_id
        LEFT OUTER JOIN pub_content pc ON pubs.pub_id = pc.pub_id
        LEFT OUTER JOIN canonical_author ca ON ca.title_id = pc.title_id
        LEFT OUTER JOIN authors a ON ca.author_id = a.author_id
        LEFT OUTER JOIN titles t on t.title_id = pc.title_id
      WHERE title_ttype in :book_types
        AND title_ttype = pub_ctype
        AND %s
      ORDER BY t.title_id, pub_dateish, pubs.pub_id""" % (fltr))

    #print(fltr)
    #print(params)
    #print(query)

    results = conn.execute(query, params).fetchall()
    ret_list = []
    pubid_dict = {}
    titleid_dict = {}
    # print(len(results))
    for row in results:
        pubid = row.pub_id
        titleid = row.title_id

        # Could/should this be done in the SQL?
        if row.pub_ctype == 'COLLECTION' and \
           row.title_ttype != 'COLLECTION':
            logging.warning('Skipping inconsistent title %d/%s/%s != pub %d/%s/%s' %
                            (pubid, row.pub_title, row.pub_ctype,
                            titleid, row.title_title, row.title_ttype))
            continue

        try:
            known_title = titleid_dict[titleid]
            try:
                known_title.add_variant(row)
            except InvalidCountryError as err:
                pass
        except KeyError:
            try:
                bk = CountrySpecificBook(row, valid_countries=countries,
                                         conn=conn)
                ret_list.append(bk)
                titleid_dict[titleid] = bk
            except InvalidCountryError as err:
                pass
    return ret_list


def get_original_books(books, year_difference_threshold=0):
    return [z for z in books
            if abs(z.best_copyright_date.year - z.first_publication.year) \
            <= year_difference_threshold]

def get_original_novels(books, valid_pub_types=None, year_difference_threshold=0):
    """
    Given a list of book-like objects, return just the ones that are:
    * original publications (based on copyright year == publication year*)
    * novels (can be overriden via valid_pub_types)

    If you set year_difference_threshold (e.g. to be 2 or more) this can be used
    as a crude filter to (hopefully) pick newish novels and avoid archive titles.
    e.g. if the first pub was a hc a year earlier, a tp published this year is
    still a somewhat new title, as opposed to an archive title from the distant
    past.

    Q: Should this be a method of PublisherBooks?
    """

    # Q: are thse definitely pub types, or are they title types?
    # (It probably doesn't matter that much, but removing ambiguity would be nice)
    if not valid_pub_types:
        valid_pub_types = {'NOVEL'}
    books_filtered_by_type = [z for z in books
                              if z.publication_type.upper() in valid_pub_types]
    return get_original_books(books_filtered_by_type, year_difference_threshold)

class PublisherBooks(object):
    """
    Class to store a collection of books by a publisher.

    This is primarily intended use for subclassing for more detailed/specific
    analysis
    """
    def __init__(self, books, conn, original_books_only=False):
        self.conn = conn

        if original_books_only:
            self.books = get_original_books(books)
        else:
            self.books = books


    def output_pub_detail(self, output_function=print):
        """
        Output details pertinent the titles and their individual publications
        """
        for i, bk in enumerate(self.books, 1):
            output_function('%3d. %s' % (i, bk))



if __name__ == '__main__':
    parser = create_parser(description='Show books published by a publisher',
                      supported_args='kpy')
    parser.add_argument('-o', dest='only_original', action='store_true',
                        help='Only report on original books being published for the first time')
    args = parse_args(sys.argv[1:], parser=parser)


    conn = get_connection()
    results = get_publisher_books(conn, args,
                                  countries=[z.upper() for z in args.countries])

    pb = PublisherBooks(results, conn, original_books_only=args.only_original)
    pb.output_pub_detail()
