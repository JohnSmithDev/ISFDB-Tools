#!/usr/bin/env python3

from collections import Counter
import pdb
import sys

from sqlalchemy.sql import text

from common import get_connection

from title_related import get_definitive_authors
from author_gender import get_author_gender_from_ids_and_then_name_cached

class Book(object):
    def __init__(self, title_id, author=''):
        self.title_id = title_id
        self.author =  author

def get_title_ids_for_year(conn, year, max_year=None, language_filter=17):
    """
    Return a generator of title_ids for all the novels in the specified year
    or year range.

    language_filter is numeric language code, 17=English
    """

    filters = []
    if max_year:
        filters.append('YEAR(title_copyright) >= :year AND YEAR(title_copyright) <= :max_year')
    else:
        filters.append('YEAR(title_copyright) = :year')

    # TODO: make these other filters configurable via args
    filters.append("title_ttype = 'NOVEL'")
    filters.append("title_non_genre = 'No'")
    filters.append("title_graphic = 'No'")
    if language_filter:
        filters.append('title_language = %d' % (language_filter))

    filter = ' AND '.join(filters)

    # See http://www.isfdb.org/wiki/index.php/Schema:canonical_author for
    # the meaning of ca_status.  I've a feeling it may be irrelevant given
    # we already filter for title_ttype though.
    query = text("""SELECT t.title_id, t.title_title
                    -- , ca.author_id, a.author_canonical
      FROM titles t
      -- LEFT OUTER JOIN canonical_author ca ON ca.title_id = t.title_id
      -- LEFT OUTER JOIN authors a ON ca.author_id = a.author_id
      WHERE %s;""" % filter)
      # WHERE ca.ca_status = 1 AND %s;""" % filter)

    rows = conn.execute(query, {'year': year, 'max_year': max_year})
    return rows

if __name__ == '__main__':
    conn = get_connection()

    year = int(sys.argv[1])
    if len(sys.argv) > 2:
        max_year = int(sys.argv[2])
    else:
        max_year = None
    rows = get_title_ids_for_year(conn, year, max_year)
    gender_counts = Counter()
    for i, row in enumerate(rows, 1):
        ORIG = """
        pseudo_name = '%s - %s / http://www.isfdb.org/cgi-bin/title.cgi?%d / ' \
                      'http://www.isfdb.org/cgi-bin/ea.cgi?%d' % \
                      (row.title_title, row.author_canonical,
                       row.title_id, row.author_id)

        gender, source = get_author_gender_from_ids_and_then_name_cached(conn,
                                                                         row.author_id,
                                                                         row.author_canonical)
        gender_counts[gender_stuff.gender] += 1
        print('%4d. %s : %s (source:%s)' % (i, gender, pseudo_name,
                                            source))
        """
        authors = get_definitive_authors(conn, Book(row.title_id))
        for j, author in enumerate(authors, 1):
            label = '%s (title_id=%d) written by author #%d %s' % (row.title_title,
                                                                   row.title_id,
                                                                   j, author)
            gender, source = get_author_gender_from_ids_and_then_name_cached(conn,
                                                                             author.id,
                                                                             author.name)
            gender_counts[gender] += 1
            print('%4d. %s : %s (source:%s)' % (i, gender, label,
                                                source))

    print(gender_counts)

