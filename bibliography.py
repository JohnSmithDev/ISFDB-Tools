#!/usr/bin/env python3
"""
Output an author's bibliography, similar to
http://www.isfdb.org/cgi-bin/ch.cgi?503

Known bugs/issues:
* Requires exact author name to be specified (although it can be any known
  alias/variant)
* Doesn't distinguish between pseudonyms
* Currently only outputs novels
* Doesn't indicate collaborations
* Hardcoded for English language editions only
* Some issues with variant editions e.g. Peter F. Hamilton, Charles Stross
"""

from collections import defaultdict, Counter, namedtuple
from functools import reduce, lru_cache
import logging
import pdb
import sys


from sqlalchemy.sql import text

from common import (get_connection, parse_args, AmbiguousArgumentsError)
from isfdb_utils import (convert_dateish_to_date, merge_similar_titles)
from author_aliases import get_author_alias_ids
from deduplicate import (DuplicatedOrMergedRecordError,
                         make_list_excluding_duplicates)

# See language table, titles.title_language
VALID_LANGUAGE_IDS = [17]

DEFAULT_TITLE_TYPES = ['NOVEL']


def safe_min(values):
    valid_values = [z for z in values if z is not None]
    if not valid_values:
        return None
    else:
        return min(valid_values)


class DuplicateBookError(DuplicatedOrMergedRecordError):
    pass

FALLBACK_YEAR = 8888

PubStuff = namedtuple('PubStuff', 'pub_id, date, format price')

class BookByAuthor(object):
    """
    Mainly a data class for all the books (and maybe other titles/pubs?) by an
    author, but with some useful helper properties.
    """
    # _tid_to_bba maps title_ids to BookByAuthor, and is used to merge duplicates
    # (as determined by common title_id)
    _tid_to_bba = {}

    @classmethod
    def reset_duplicate_cache(cls):
        """
        If you are processing multiple bibliographies, possibly for the same
        or related author (e.g. variant, maybe co-author too), you need to clear
        out the cache, otherwise later queries for bibliographies will return
        zero or reduced rows.
        """
        cls._tid_to_bba = {}

    def __init__(self, row, author='Author', allow_duplicates=False):
        # Q: I don't see that allow_duplicates is ever used?
        self.title_id = row['title_id']
        self.parent_id = row['title_parent']
        self.title_title = row['title_title'] # Use the .title property over this

        self.copyright_date = convert_dateish_to_date(row['t_copyright'])
        self._copyright_dates = [self.copyright_date]

        self.pub_id = row['pub_id']
        self.pub_title = row['pub_title']
        self.publication_date = convert_dateish_to_date(row['p_publication_date'])
        self._publication_dates = [self.publication_date]
        self.isbns = [row['pub_isbn']]

        # Q: should this count twice if title and pub_title are the same?
        valid_titles = [z for z in [self.title_title, self.pub_title] if z]
        self._titles = Counter(valid_titles)

        self.author = author


        self.pub_stuff = PubStuff(self.publication_date, self.publication_date,
                                  row['pub_ptype'], row['pub_price'])
        self.all_pub_stuff = [self.pub_stuff]


        key = self.parent_id or self.title_id
        # self._title_id_to_titles[key].update([self.title, self.pub_title])
        # self._publication_dict[key].update([self.copyright_date, self.publication_date])

        try:
            other = self._tid_to_bba[key]
            other.merge_in_fields(self)
            raise DuplicateBookError('%s (id=%d) already known as %s (id=%d)' %
                                     (self.title, self.title_id,
                                      other.title, other.title_id))

        except KeyError:
            self._tid_to_bba[key] = self


    def merge_in_fields(self, other):
        self._titles.update(other._titles)
        self._copyright_dates.extend(other._copyright_dates)
        self._publication_dates.extend(other._publication_dates)
        self.isbns.extend(other.isbns)
        self.all_pub_stuff.extend(other.all_pub_stuff)

    @property
    def earliest_copyright_date(self):
        return safe_min(self._copyright_dates)

    @property
    def earliest_publication_date(self):
        return safe_min(self._publication_dates)

    @property
    def prioritized_titles(self):
        return [z[0] for z in self._titles.most_common()]

    @property
    def all_titles(self):
        return ' aka '.join(self.prioritized_titles)

    @property
    @lru_cache()
    def title(self):
        return self.prioritized_titles[0]

    @property
    @lru_cache()
    def year(self):
        dt = safe_min([self.earliest_copyright_date, self.earliest_publication_date])
        if not dt:
            return FALLBACK_YEAR
        else:
            return dt.year

    @property
    def pub_stuff_string(self):
        with_dates = [z for z in self.all_pub_stuff
                      if z.date and 1800 <= z.date.year <= 2100]
        date_sorted = sorted(with_dates, key=lambda z: z.date)
        year_to_stuff = {} # deliberately not using defaultdict
        for year in range(MIN_PUB_YEAR, MAX_PUB_YEAR+1):
            year_to_stuff[year] = []
            # TODO: make this more efficient
            for stuff in date_sorted:
                if stuff.date.year == year:
                    year_to_stuff[year].append(stuff)
        counts = [len(v) for k, v in sorted(year_to_stuff.items())]

        def num_rep(v):
            if v >= 10:
                return 'X'
            elif v == 0:
                return '.'
            else:
                return str(v)
        return ''.join([num_rep(z) for z in counts])


    def __repr__(self):
        return '%s [%d]' % (self.title, self.year)


MIN_PUB_YEAR = 1990
MAX_PUB_YEAR = 2020

def get_raw_bibliography(conn, author_ids, author_name, title_types=DEFAULT_TITLE_TYPES):
    """
    Pulled out of get_bibliography() when testing where a bug was occurring;
    probably not amazingly useful without the post-processing, but it's here
    if you want it...
    """
    # title_copyright is not reliably populated, hence the joining to pubs
    # for their date as well.
    # Or is that just an artefact of 0 day-of-month causing them to be output as None?
    # NB: title_types and pub_ctypes are not the same, so if/when we extend
    #     this beyond NOVEL, that code will need to change
    query = text("""SELECT t.title_id, t.title_parent, t.title_title,
          CAST(t.title_copyright AS CHAR) t_copyright,
          t.series_id, t.title_seriesnum, t.title_seriesnum_2,
          p.pub_id, p.pub_title, CAST(p.pub_year as CHAR) p_publication_date,
          p.pub_isbn, p.pub_price, p.pub_ptype
    FROM canonical_author ca
    LEFT OUTER JOIN titles t ON ca.title_id = t.title_id
    LEFT OUTER JOIN pub_content pc ON t.title_id = pc.title_id
    LEFT OUTER JOIN pubs p ON pc.pub_id = p.pub_id
    WHERE author_id IN :author_ids
      AND t.title_ttype IN :title_types
      AND p.pub_ctype IN :title_types
      AND title_language IN :title_languages
    ORDER BY t.title_id, p.pub_year; """)
    rows = conn.execute(query, {'author_ids':author_ids,
                                'title_types': title_types,
                                'title_languages': VALID_LANGUAGE_IDS})
    # print(len(rows)) # This only works if you do a .fetchall() above
    return rows

def get_bibliography(conn, author_ids, author_name, title_types=DEFAULT_TITLE_TYPES):
    """
    Given a list of author_ids, return a sorted bibliography.

    author_name is a bit of a hack to avoid having to do another lookup on
    the authors table (which *might* have complications with multiple matches
    e.g. an author with variant names, that a book has been issued under both
    variants?)
    """
    rows = get_raw_bibliography(conn, author_ids, author_name, title_types)

    BookByAuthor.reset_duplicate_cache()

    def make_bba(stuff, allow_duplicates):
        """
        Curried wrapper to BookByAuthor class.
        The use of author_names[0] is a bit of a hack - TODO: better
        """
        bba =  BookByAuthor(stuff, author=author_name,
                            allow_duplicates=allow_duplicates)
        # if bba.year is None or bba.year == FALLBACK_YEAR:
        #    logging.warning('Year is None or %s for %s (possibly unpublished?' %
        #                    (FALLBACK_YEAR, bba))
        return bba

    books = make_list_excluding_duplicates(
        rows, make_bba,
        allow_duplicates=False, duplication_exception=DuplicateBookError)

    if not books:
        # Hack for 1975 Campbell New Writer winner P. J. Plauger, who seems to only
        # have 2 novels, both of which only ever printed as magazine serializations?
        logging.warning('No books found for %s/%s' % (author_ids, author_name))
        return []
    # rows.close() # Doesn't fix the re-run failure
    return sorted(books, key=lambda z: z.year)



def postprocess_bibliography(raw_rows):
    # THIS SEEMS TO BE NO LONGER USED???
    title_id_to_titles = defaultdict(set)
    publication_dict = defaultdict(set)
    # TODO: might be nice to order the titles by most popular first?
    # TODO: better to call merge_similar_titles() here?
    for row in raw_rows:
        key = row['title_parent'] or row['title_id']
        title_id_to_titles[key].update([row['title_title'], row['pub_title']])
        publication_dict[key].update([convert_dateish_to_date(row['t_copyright']),
                                   convert_dateish_to_date(row['p_publication_date'])])

    titles_to_first_pub = {}
    for tid, titles in title_id_to_titles.items():
        pubdates = [z for z in publication_dict[tid] if z is not None]
        titles_to_first_pub[tuple(titles)] = min(pubdates)
    return sorted(titles_to_first_pub.items(), key=lambda z: z[1])

def get_author_bibliography(conn, author_names):
    # author_ids = get_author_alias_ids(conn, author_names)
    author_name = author_names[0]
    author_ids = get_author_alias_ids(conn, author_name)
    if not author_ids:
        raise AmbiguousArgumentsError('Do not know author "%s"' % (author_names))
    # print(author_ids)
    bibliography = get_bibliography(conn, author_ids, author_name)
    return bibliography

if __name__ == '__main__':
    args = parse_args(sys.argv[1:],
                      description="List an author's bibliography",
                      supported_args='av')

    conn = get_connection()

    bibliography = get_author_bibliography(conn, args.exact_author)
    for i, bk in enumerate(bibliography, 1):
        print('%2d. %s %s [%d]' % (i, bk.pub_stuff_string, bk.all_titles, bk.year))
        # pdb.set_trace()

