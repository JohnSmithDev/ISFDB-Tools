#!/usr/bin/env python3

from collections import Counter
import pdb
import sys

from sqlalchemy.sql import text

from common import get_connection, parse_args, get_filters_and_params_from_args

from title_related import get_definitive_authors
from author_gender import get_author_gender_from_ids_and_then_name_cached
from isfdb_utils import safe_year_from_date, convert_dateish_to_date
from gender_analysis import year_data_as_cells

class Book(object):
    def __init__(self, title_id, author=''):
        self.title_id = title_id
        self.author =  author

#def get_title_ids_for_year(conn, year, max_year=None, language_filter=17,
#                           tags=None):
def get_title_ids_for_year(conn, args, language_filter=17):
    """
    Return a generator of title_ids for all the novels in the specified year
    or year range, and optionally matching one or more tags

    language_filter is numeric language code, 17=English
    """

    fltr, params = get_filters_and_params_from_args(args,
                                                    {'year': 'title_copyright'})
    # pdb.set_trace()


    joins = []
    filters = []
    if fltr:
        filters.append(fltr)

    THESE_ARE_NOW_DONE_VIA_ARGS_FLTR_PARAMS = """
    if max_year:
        filters.append('YEAR(title_copyright) >= :year AND YEAR(title_copyright) <= :max_year')
    else:
        filters.append('YEAR(title_copyright) = :year')
    """

    if 'exact_tag' in params or 'tag' in params:
        # (Fixed) Bug: as things stand, this will count titles multiple times if
        # multiple ISFDB users have tagged them with the same tag e.g. as of
        # Sep 2019, "Neuromancer" has been tagged "cyberpunk" 3 times
        # http://www.isfdb.org/cgi-bin/title.cgi?1475
        # This has been fixed by doing SELECT DISTINCT further down, but maybe
        # that's not an optimal solution?
        joins.extend(['LEFT OUTER JOIN tag_mapping tm ON tm.title_id = t.title_id ',
                     'LEFT OUTER JOIN tags on tags.tag_id = tm.tag_id'])
        # This next bit now done via fltr above
        # filters.append('tags.tag_name in :tags')

    # TODO: make these other filters configurable via args
    filters.append("title_ttype = 'NOVEL'")
    filters.append("title_non_genre = 'No'")
    filters.append("title_graphic = 'No'")
    if language_filter:
        filters.append('title_language = %d' % (language_filter))

    filter = ' AND '.join(filters)
    extra_joins = '\n' + '\n'.join(joins)


    # See http://www.isfdb.org/wiki/index.php/Schema:canonical_author for
    # the meaning of ca_status.  I've a feeling it may be irrelevant given
    # we already filter for title_ttype though.
    query = text("""SELECT DISTINCT t.title_id, t.title_title,
                    CAST(t.title_copyright AS CHAR) copyright_date
      FROM titles t
      %s
      WHERE %s;""" % (extra_joins, filter))

    rows = conn.execute(query, params)
    return rows



def normalize_gender_source(src):
    # TODO: this should be moved into gender_analysis.py, and used by
    # analyse_authors_by_gender()
    if not src:
        return 'unknown'
    elif ':' in src:
        ret, _ = src.split(':', 1)
        return ret
    else:
        return src

def generate_gender_stats(conn, books, period='year', output_function=print):

    gender_counts = Counter()
    pgs_counts = Counter() # prefix/period/gender/source
    for i, row in enumerate(books, 1):
        authors = get_definitive_authors(conn, Book(row.title_id))
        for j, author in enumerate(authors, 1):
            if not author.id:
                # There are a few (six as of Oct 2019) orphaned canonical_author
                # records.  See https://sourceforge.net/p/isfdb/bugs/739/
                # and https://github.com/JohnSmithDev/ISFDB-Tools/issues/17 -
                # but we shall ignore them
                continue
            # print(row.copyright_date)
            dt = convert_dateish_to_date(row.copyright_date)
            label = '%s (title_id=%d) written by author #%d %s [%s]' % \
                    (row.title_title,
                     row.title_id,
                     j, author, dt)
            gender, source = get_author_gender_from_ids_and_then_name_cached(conn,
                                                                             author.id,
                                                                             author.name)
            gender_counts[gender] += 1
            output_function('%4d. %s : %s (source:%s)' % (i, gender, label,
                                                source))
            sanitised_source = normalize_gender_source(source)
            if period == 'year':
                if gender:
                    k = (dt.year, gender, sanitised_source)
                else:
                    k = (dt.year, 'unknown')
            else:
                raise Exception('Dunno how to handle prefix/period "%s"' % (period))
            pgs_counts[k] += 1



    output_function(gender_counts)
    return pgs_counts



if __name__ == '__main__':
    args = parse_args(sys.argv[1:],
                      description='Report on gender balance for published novels',
                      supported_args='gy')
    # pdb.set_trace()

    conn = get_connection()

    ORIG = """
    year = int(sys.argv[1])
    if len(sys.argv) > 2:
        max_year = int(sys.argv[2])
    else:
        max_year = None
    """


    # rows = get_title_ids_for_year(conn, year, max_year, tags=['science fiction'])
    rows = get_title_ids_for_year(conn, args)
    stats = generate_gender_stats(conn, rows)

    # for k, c in sorted(stats.items()):
    #     print(k, c)

    cells = year_data_as_cells(stats)
    for row in cells:
        print(row)

