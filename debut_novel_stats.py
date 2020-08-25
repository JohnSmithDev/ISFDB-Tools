#!/usr/bin/env python3
"""
Report on which novels a publisher published were debuts.

"""

from collections import namedtuple
from datetime import timedelta, date
#import json
# from os.path import basename
import logging
import pdb
import sys

from sqlalchemy.sql import text


from common import get_connection, parse_args, get_filters_and_params_from_args
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
AuthorAndTitleStuff = namedtuple('AuthorAndTitleStuff', 'author_id, author, title_id, title')

class DebutStats(object):
    def __init__(self, books, do_prefilter=True):

        if do_prefilter:
            novels = [z for z in books if z.publication_type.lower() == 'novel']
            new_novels = [z for z in novels
                          if z.best_copyright_date.year == z.first_publication.year]
        else:
            new_novels = books
        self._process(new_novels)


    def _process(self, books):

        self.book_author_count = 0
        # Dict mapping author name to book details; this is to avoid counting
        # an author twice
        self.debut_details = {}

        for i, bk in enumerate(books, 1):
            for (author_id, author_name) in sorted(bk.author_id_to_name.items()):
                author_ids = [author_id]
                other_author_stuff = get_real_author_id_and_name(conn, author_id)
                if other_author_stuff:
                    author_ids.extend([z.id for z in other_author_stuff])
                self.book_author_count += 1
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
                debut_novel = bib[0]

                # Check the title IDs and the title parent IDs to be (hopefully)
                # sure of finding a match
                debut_ids = set([debut_novel.title_id])
                if debut_novel.parent_id:
                    debut_ids.add(debut_novel.parent_id)
                bk_ids = set([bk.title_id])
                if bk.title_parent:
                    bk_ids.add(bk.title_parent)
                if bk_ids.intersection(debut_ids):
                    if author_name not in self.debut_details:
                        details = AuthorAndTitleStuff(author_id, author_name,
                                                      bk.title_id, bk.title)
                        self.debut_details[author_name] = details
                    # print('debut_ids=%s; bk_ids=%s' % (debut_ids, bk_ids))
                    # print(bk.copyright_date, bk.best_copyright_date)

        # print(self.debut_details)

    @property
    def debut_authors(self):
        return self.debut_details.keys()

    @property
    def debut_count(self):
        return len(self.debut_authors)

    def __repr__(self):
        return '%2d of %3d (%2d%%) new novels/authors were debuts : %s' % \
            (self.debut_count, self.book_author_count,
             100 * self.debut_count / self.book_author_count,
             ', '.join(sorted(self.debut_authors))
            )


def debut_report(conn, args, output_function=print):

    results = get_publisher_books(conn, args,
                                  countries=[z.upper() for z in args.countries])
    ds = DebutStats(results, do_prefilter=True)

    if ds.book_author_count:
        output_function('%s. %2d of %3d (%2d%%) new novels/authors were debuts : %s' %
                        (args.year, ds.debut_count, ds.book_author_count,
                         100 * ds.debut_count / ds.book_author_count,
                         ', '.join(sorted(ds.debut_authors))
                        ))

if __name__ == '__main__':
    args = parse_args(sys.argv[1:],
                      description='Report on debut novels published by a publisher',
                      supported_args='kpy')

    conn = get_connection()
    debut_report(conn, args)
