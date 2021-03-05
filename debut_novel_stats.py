#!/usr/bin/env python3
"""
Report on which novels a publisher published were debuts, or an author's
2nd, 3rd, nth, etc novel.

"""

from collections import namedtuple, defaultdict
from datetime import timedelta, date
from functools import lru_cache
from itertools import chain
#import json
# from os.path import basename
import logging
import pdb
import sys

from sqlalchemy.sql import text

from common import (get_connection, parse_args, get_filters_and_params_from_args,
                    create_parser)
# from isfdb_utils import convert_dateish_to_date, pretty_list

from publisher_books import (get_publisher_books, PublisherBooks,
                             get_original_novels)
from bibliography import get_bibliography
from author_aliases import get_real_author_id_and_name, get_author_alias_ids
from publisher_variants import PUBLISHER_VARIANTS


AUTHORS_TO_IGNORE = {'uncredited'}


# Maps author_id to list of something.  A global variable so that once we've
# looked up an author's bibliography, we can re-use that data if they come up
# again
bibliographies = {}


# I'm sure I have tuples for this already, although maybe in another repo?
# ... although I've now added book, so this isn't the same as the other
# namedtuples
AuthorAndTitleStuff = namedtuple('AuthorAndTitleStuff', 'author_id, author, '
                                 'title_id, title, book')

NthAverages = namedtuple('NthAverages', 'mean_nth, weighted_mean_nth, ' + \
                         'median_nth, weighted_median_nth')

def collate_title_ids(bk):
    bk_ids = set()
    # Yay for inconsistent attribute names :-(
    for a in ['title_id', 'parent_id', 'title_parent']:
        try:
            x = getattr(bk, a)
            if x:
                bk_ids.add(x)
        except AttributeError:
            pass
    return bk_ids

def is_same_book(bk1, bk2):
    bk1_ids = collate_title_ids(bk1)
    bk2_ids = collate_title_ids(bk2)
    return bk1_ids.intersection(bk2_ids)


# Now moved to publisher_books.py
def xxx_get_original_novels(books, valid_pub_types=None, year_difference_threshold=0):
    """
    Given a list of book-like objects, return just the ones that are:
    * original publications (based on copyright year == publication year*)
    * novels (can be overriden via valid_pub_types)

    If you set year_difference_threshold (e.g. to be 2 or more) this can be used
    as a crude filter to (hopefully) pick newish novels and avoid archive titles.
    e.g. if the first pub was a hc a year earlier, a tp published this year is
    still a somewhat new title, as opposed to an archive title from the distant
    past.
    """

    if not valid_pub_types:
        valid_pub_types = {'NOVEL'}
    books_filtered_by_type = [z for z in books
                              if z.publication_type.upper() in valid_pub_types]
    return [z for z in books_filtered_by_type
            if abs(z.best_copyright_date.year - z.first_publication.year) \
            <= year_difference_threshold]


class DebutStats(PublisherBooks):
    def __init__(self, books, conn, original_books_only=True):
        super().__init__(books, conn, original_books_only)
        self._process()


        ORIG2 = '''
        self.conn = conn

        if do_prefilter:
            # Now refactored as this is of more general use
            ORIG = """
            novels = [z for z in books if z.publication_type.lower() == 'novel']
            self.books = [z for z in novels
                          if z.best_copyright_date.year == z.first_publication.year]
            """
            self.books = get_original_novels(books)
        else:
            self.books = books
        self._process()
        '''

    def _process(self):
        self.all_details = []
        # Dict mapping author name to book details; this is to avoid counting
        # an author twice
        self.debut_details = {}

        for i, bk in enumerate(self.books, 1):
            for (author_id, author_name) in sorted(bk.author_id_to_name.items()):
                if author_name in AUTHORS_TO_IGNORE:
                    continue
                details = AuthorAndTitleStuff(author_id, author_name,
                                              bk.title_id, bk.title, bk)
                self.all_details.append(details)
                author_ids = [author_id]
                # Not sure why I originally chose get_real_author_id_and_name(), it seems
                # to only pick up parent authors, and we only need IDs here.
                # Had to filter out gestalt pseudonyms (the 2 argument) - this probably needs
                # revisiting/pondering...
                # other_author_stuff = get_real_author_id_and_name(self.conn, author_id)
                other_author_stuff = get_author_alias_ids(self.conn, author_name, 2)
                if other_author_stuff:
                    # author_ids.extend([z.id for z in other_author_stuff])
                    author_ids.extend(other_author_stuff)
                try:
                    bib = bibliographies[author_id]
                except KeyError:
                    bib = get_bibliography(self.conn,
                                           author_ids,
                                           author_name)
                    for aid in author_ids:
                        bibliographies[aid] = bib
                if len(bib) == 0:
                    # This will come up if a novel has never been published standalone,
                    # but only serialized or in an anthology
                    # e.g. http://www.isfdb.org/cgi-bin/title.cgi?973501
                    logging.warning('No bibliography found for author %s (%d)' %
                                    (author_name, author_id))
                    # pdb.set_trace()
                    continue

                # Check the title IDs and the title parent IDs to be (hopefully)
                # sure of finding a match
                debut_novel = bib[0]
                if is_same_book(debut_novel, bk):
                    if author_name not in self.debut_details:
                        self.debut_details[author_name] = details
                    # print('debut_ids=%s; bk_ids=%s' % (debut_ids, bk_ids))
                    # print(bk.copyright_date, bk.best_copyright_date)

        for i, bk in enumerate(self.all_details, 1):
            # print(i,bk)
            pass

    @property
    def book_author_count(self):
        # Use len(self.books) if you want to know the number of books, regardless
        # of the number of authors
        return len(self.all_details)

    @property
    def debut_authors(self):
        return self.debut_details.keys()

    @property
    def debut_count(self):
        return len(self.debut_authors)

    @property
    def distinct_authors(self):
        raw_authors = [bk.author_id_to_name.values() for bk in self.books]
        flattened_authors = chain(*raw_authors)
        ret = set(flattened_authors)
        return ret

    @property
    def nth_book_details(self):
        """
        Note that the nth book details returned start at 1, whereas other
        code in this module uses 0.  (The other code doesn't display any number
        to the user, whereas the expectation is that these values will be shown
        or used in some other calculation such as average nth book.
        """
        ret = []
        for bk_stuff in self.all_details:
            bib = bibliographies[bk_stuff.author_id]
            for i, bib_book in enumerate(bib, 1):
                if is_same_book(bk_stuff.book, bib_book):
                    ret.append((i, bk_stuff))
                    break
            else:
                logging.warning(f'Failed to find {bk_stuff.book.title} in bibliography '
                                f'for {bk_stuff.author} ({bk_stuff.author_id})')
        return ret

    @property
    @lru_cache()
    def average_nth_book(self):
        """
        Returns a (named)tuple of
        * mean nth book
        * weighted mean nth book
        * median nth book
        * weighted median nth book
        The weighting is to try to address the bloating that books by multiple
        authors can cause, by dividing the nth value by the number of authors.
        (This only looks at the book in question; it doesn't care about any
        historical collaborations.)
        """
        nth_items = [z[0] for z in self.nth_book_details]
        weighted_nth_items = [weighted_nth_book(z[0], z[1].book) for z in self.nth_book_details]
        sorted_items = sorted(nth_items)
        sorted_weighted_items = sorted(weighted_nth_items)
        median_idx = int(len(nth_items) / 2)
        if nth_items:
            return NthAverages(sum(nth_items) / len(nth_items) ,
                               sorted_items[median_idx],
                               sum(weighted_nth_items) / len(nth_items) ,
                               sorted_weighted_items[median_idx])
        else:
            return NthAverages(0, 0, 0, 0)


    def output_nth_detail(self, output_function=print):
        """
        Output details pertinent to whether the books are debuts or nth novels
        """
        details = self.nth_book_details
        max_nth = max([z[0] for z in details])
        for nth, bk in sorted(details):
            weighted_nth = weighted_nth_book(nth, bk.book)
            pretty_nth = pretty_ordinal(nth)
            nth_string = f'{pretty_nth} [weighted={weighted_nth}]'
            output_function('%25s\'s %3s book: "%s"' % (bk.author,
                                                            nth_string,
                                                            bk.title))

    def xxx_output_pub_detail(self, output_function=print):
        """
        NOW MOVED TO PARENT CLASS
        Output details pertinent the titles and their individual publications
        """
        for i, bk in enumerate(self.books, 1):
            output_function('%3d. %s' % (i, bk))

    def __repr__(self):
        if self.debut_authors:
            debut_author_list = ', '.join(sorted(self.debut_authors))
        else:
            debut_author_list = 'N/A'
        all_books_bit = '%d new novels' % (len(self.books))
        all_authors_bit = '%d distinct authors' % (len(self.distinct_authors))
        #  100 * self.debut_count / len(self.books))

        return 'Of %s by %s, %d books had a debut author | %s' % (
            all_books_bit, all_authors_bit, self.debut_count,
            debut_author_list)

        BLAH ="""

 / %3d (%2d%%) new novels/authors were debuts : %s' % \
all_books_bit, all_authors_bit,
             self.book_author_count, 100 * self.debut_count / self.book_author_count,
             debut_author_list)
        """

def pretty_ordinal(n):
    """Return '1st', '2nd', '3rd' etc for a given integer"""
    # Isn't this basically the same as isfdb_utils.pretty_nth ?
    pos_n = abs(n)
    if (pos_n % 100) in (11, 12, 13):
        return f'{n}th'
    elif (pos_n % 10) == 1:
        return f'{n}st'
    elif (pos_n % 10) == 2:
        return f'{n}nd'
    elif (pos_n % 10) == 3:
        return f'{n}rd'
    else:
        return f'{n}th'



def weighted_nth_book(nth, bk):
    num_authors = len(bk.authors)
    if num_authors == 0: # Assume anonymous, unknown, etc
        return 0
    else:
        return max(1, int(nth / len(bk.authors)))

def split_books_by_year(books):
    """
    Given a list/iterable of books, return a sorted list of tuples of
    (year, [list of that years books])
    """
    # I'm sure there's a more mapreducy way of doing this.
    year_to_books = defaultdict(list)
    bad_years = []
    for bk in books:
        if bk.year and bk.year not in (8888,):
            year_to_books[bk.year].append(bk)
        else:
            bad_years.append(bk)
    if bad_years:
        logging.warning(f'Found {len(bad_years)} books with no year defined, which will be ignored')
    return sorted(year_to_books.items())

# This should be controlled by CLI arg (-n is now supported in the common arg
# handling code, but may need some more massaging/testing before being workable
# here)
# VALID_BOOK_TYPES = ['NOVEL', 'CHAPBOOK']
VALID_BOOK_TYPES = ['NOVEL']

def debut_report(conn, args, output_function=print):
    """
    Besides outputting a textual report, returns a sorted list of
    (year, DebutStats1.  Only years that had books published will be in the
    returned value, but this may include years where there were no debut novels.)
    """

    ret = []
    results = get_publisher_books(conn, args,
                                  countries=[z.upper() for z in args.countries],
                                  book_types=VALID_BOOK_TYPES)

    yearly_results = split_books_by_year(results)
    for year, all_published_books in sorted(yearly_results):
        new_novels = get_original_novels(all_published_books, valid_pub_types=VALID_BOOK_TYPES)
        non_backlist_novels = get_original_novels(all_published_books,
                                                  valid_pub_types=VALID_BOOK_TYPES,
                                                  year_difference_threshold=5)
        num_backlist_novels = len(all_published_books) - len(non_backlist_novels)
        output_function('Of %d novels published in %d, %d (%d%%) were brand new novels and %d classic' %
                        (len(all_published_books), year,
                         len(new_novels), 100 * len(new_novels) / len(all_published_books),
                         num_backlist_novels
                        ))
        ds = DebutStats(new_novels, conn, original_books_only=False)

        if ds.book_author_count:
            mean, weighted_mean, median, weighted_median= ds.average_nth_book
            output_function('%s. %s (mean %dth/%dth book, median %dth/%dth book)' %
                            (year, ds, mean, weighted_mean, median, weighted_median))
            try:
                if args.show_nth_detail:
                    ds.output_nth_detail(output_function)
                if args.show_pub_detail:
                    ds.output_pub_detail(output_function)
            except AttributeError: # Why might this blow up?
                pass
        ret.append((year, ds))
        if args.verbose:
            for nth, bk in ds.nth_book_details:
                pretty_nth = pretty_ordinal(nth)
                output_function(f'{pretty_nth} novel by {bk.author} : {bk.title}')
    return ret


if __name__ == '__main__':
    # TODO: add -n for title type support
    parser = create_parser(description='Report on debut novels published by a publisher',
                           supported_args='kpy')
    parser.add_argument('-d', dest='show_nth_detail', action='store_true',
                        help='Enable detailed output re. debut/nth novel')
    parser.add_argument('-D', dest='show_pub_detail', action='store_true',
                        help='Enable detailed output re. titles and publications')
    args = parse_args(sys.argv[1:], parser=parser)


    conn = get_connection()
    debut_report(conn, args)
