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

from collections import defaultdict, Counter
from functools import reduce, lru_cache
import pdb
import sys


from sqlalchemy.sql import text

from common import (get_connection, parse_args, AmbiguousArgumentsError)
from isfdb_utils import (convert_dateish_to_date, merge_similar_titles)
from author_aliases import get_author_alias_ids


# See language table, titles.title_language
VALID_LANGUAGE_IDS = [17]

def safe_min(values):
    valid_values = [z for z in values if z is not None]
    if not valid_values:
        return None
    else:
        return min(valid_values)


class DuplicateBookError(Exception):
    pass

class BookByAuthor(object):
    # Older code, don't think we need this now
    _title_id_to_titles = defaultdict(set)
    _publication_dict = defaultdict(set) # title_id => {dates}
    # _titles_to_first_pub = {}

    _tid_to_bba = {}


    def __init__(self, row, author='Author', allow_duplicates=False):
        self.title_id = row['title_id']
        self.parent_id = row['title_parent']
        self.title_title = row['title_title'] # Use the .title property over this

        self.copyright_date = convert_dateish_to_date(row['t_copyright'])
        self._copyright_dates = [self.copyright_date]

        self.pub_id = row['pub_id']
        self.pub_title = row['pub_title']
        self.publication_date = convert_dateish_to_date(row['p_publication_date'])
        self._publication_dates = [self.publication_date]

        # Q: should this count twice if title and pub_title are the same?
        valid_titles = [z for z in [self.title_title, self.pub_title] if z]
        self._titles = Counter(valid_titles)


        self.author = author

        key = self.parent_id or self.title_id
        self._title_id_to_titles[key].update([self.title, self.pub_title])
        self._publication_dict[key].update([self.copyright_date, self.publication_date])

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

    @property
    def earliest_copyright_date(self):
        return safe_min(self._copyright_dates)

    @property
    def earliest_publication_date(self):
        return safe_min(self._publication_dates)

    @property
    def all_titles(self):
        return ' aka '.join([z[0] for z in self._titles.most_common()])


    @property
    @lru_cache()
    def title(self):
        return self.all_titles[0]

    @property
    @lru_cache()
    def year(self):
        dt = safe_min([self.earliest_copyright_date, self.earliest_publication_date])
        if not dt:
            return None
        else:
            return dt.year

    def __repr__(self):
        return '%s [%d]' % (self.title, self.year)

def get_bibliography(conn, author_ids):
    # title_copyright is not reliably populated, hence the joining to pubs
    # for their date as well.
    # Or is that just an artefact of 0 day-of-month causing them to be output as None?
    # NB: title_types and pub_ctypes are not the same, so if/when we extend
    #     this beyond NOVEL, that code will need to change
    query = text("""SELECT t.title_id, t.title_parent, t.title_title,
          CAST(t.title_copyright AS CHAR) t_copyright,
          t.series_id, t.title_seriesnum, t.title_seriesnum_2,
          p.pub_id, p.pub_title, CAST(p.pub_year as CHAR) p_publication_date
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
                                'title_types': ['NOVEL'],
                                'title_languages': VALID_LANGUAGE_IDS})
    # return postprocess_bibliography(rows)

    def make_list_excluding_duplicates(accumulator, new_value):
        if not accumulator:
            accumulator = []
        try:
            accumulator.append(BookByAuthor(new_value,
                                            allow_duplicates=False))
        except DuplicateBookError:
            pass
        return accumulator

    books = reduce(make_list_excluding_duplicates, rows, None)
    return sorted(books, key=lambda z: z.year)



def postprocess_bibliography(raw_rows):
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

def get_author_bibliography(conn, author_name):
    author_ids = get_author_alias_ids(conn, author_name)
    if not author_ids:
        raise AmbiguousArgumentsError('Do not know author "%s"' % (author_name))
    bibliography = get_bibliography(conn, author_ids)
    return bibliography

if __name__ == '__main__':
    args = parse_args(sys.argv[1:],
                      description="List an author's bibliography",
                      supported_args='av')

    conn = get_connection()
    bibliography = get_author_bibliography(conn, args.exact_author)
    for i, bk in enumerate(bibliography, 1):
        print('%2d. %s [%d]' % (i, bk.all_titles, bk.year))
