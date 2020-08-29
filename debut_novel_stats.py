#!/usr/bin/env python3
"""
Report on which novels a publisher published were debuts.

"""

from collections import namedtuple, defaultdict
from datetime import timedelta, date
#import json
# from os.path import basename
import logging
import pdb
import sys

from sqlalchemy.sql import text


from common import (get_connection, parse_args, get_filters_and_params_from_args,
                    create_parser)
# from isfdb_utils import convert_dateish_to_date, pretty_list

from publisher_books import get_publisher_books
from bibliography import get_bibliography
from author_aliases import get_real_author_id_and_name
from publisher_variants import PUBLISHER_VARIANTS

# Maps author_id to list of something.  A global variable so that once we've
# looked up an author's bibliography, we can re-use that data if they come up
# again
bibliographies = {}


# I'm sure I have tuples for this already, although maybe in another repo?
# ... although I've now added book, so this isn't the same as the other
# namedtuples
AuthorAndTitleStuff = namedtuple('AuthorAndTitleStuff', 'author_id, author, '
                                 'title_id, title, book')


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


class DebutStats(object):
    def __init__(self, books, do_prefilter=True):

        if do_prefilter:
            novels = [z for z in books if z.publication_type.lower() == 'novel']
            self.books = [z for z in novels
                          if z.best_copyright_date.year == z.first_publication.year]
        else:
            self.books = books
        self._process()


    def _process(self):
        self.all_details = []
        # Dict mapping author name to book details; this is to avoid counting
        # an author twice
        self.debut_details = {}

        for i, bk in enumerate(self.books, 1):
            for (author_id, author_name) in sorted(bk.author_id_to_name.items()):
                details = AuthorAndTitleStuff(author_id, author_name,
                                              bk.title_id, bk.title, bk)
                self.all_details.append(details)
                author_ids = [author_id]
                other_author_stuff = get_real_author_id_and_name(conn, author_id)
                if other_author_stuff:
                    author_ids.extend([z.id for z in other_author_stuff])
                try:
                    bib = bibliographies[author_id]
                except KeyError:
                    bib = get_bibliography(get_connection(),
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
    def average_nth_book(self):
        nth_items = [z[0] for z in self.nth_book_details]
        weighted_nth_items = [weighted_nth_book(z[0], z[1].book) for z in self.nth_book_details]
        sorted_items = sorted(nth_items)
        sorted_weighted_items = sorted(weighted_nth_items)
        median_idx = int(len(nth_items) / 2)
        if nth_items:
            return (sum(nth_items) / len(nth_items) , sorted_items[median_idx],
                    sum(weighted_nth_items) / len(nth_items) ,
                    sorted_weighted_items[median_idx])
        else:
            return 0, 0, 0, 0

    def output_detail(self, output_function=print):
        details = self.nth_book_details
        max_nth = max([z[0] for z in details])
        # TODO: work out optimal width
        for nth, bk in sorted(details):
            weighted_nth = weighted_nth_book(nth, bk.book)
            nth_string = f'#{nth} [weighted={weighted_nth}]'
            output_function('Book %3s: "%s" by %s' % (nth_string,
                                                      bk.title, bk.author))

    def __repr__(self):
        return '%2d of %3d (%2d%%) new novels/authors were debuts : %s' % \
            (self.debut_count, self.book_author_count,
             100 * self.debut_count / self.book_author_count,
             ', '.join(sorted(self.debut_authors))
            )

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
    for bk in books:
        year_to_books[bk.year].append(bk)
    return sorted(year_to_books.items())

def debut_report(conn, args, output_function=print):

    results = get_publisher_books(conn, args,
                                  countries=[z.upper() for z in args.countries],
                                  book_types=['NOVEL'])

    yearly_results = split_books_by_year(results)
    for year, books in yearly_results:
        ds = DebutStats(books, do_prefilter=True)

        if ds.book_author_count:
            mean, weighted_mean, median, weighted_median= ds.average_nth_book
            output_function('%s. %s (mean %dth/%dth book, median %dth/%dth book)' %
                            (year, ds, mean, weighted_mean, median, weighted_median))
            if args.show_detail:
                ds.output_detail(output_function)


if __name__ == '__main__':
    parser = create_parser(description='Report on debut novels published by a publisher',
                           supported_args='kpy')
    parser.add_argument('-d', dest='show_detail', action='store_true',
                        help='Enable detailed output')
    args = parse_args(sys.argv[1:], parser=parser)


    conn = get_connection()
    debut_report(conn, args)
