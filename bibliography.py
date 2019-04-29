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

from collections import defaultdict
import pdb
import sys


from sqlalchemy.sql import text

from common import (get_connection, parse_args, AmbiguousArgumentsError)
from utils import convert_dateish_to_date
from author_aliases import get_author_alias_ids


# See language table, titles.title_language
VALID_LANGUAGE_IDS = [17]


def get_bibliography(conn, author_ids):
    # title_copyright is not reliably populated, hence the joining to pubs
    # for their date as well.
    # Or is that just an artefact of 0 day-of-month causing them to be output as None?
    # NB: title_types and pub_ctypes are not the same, so if/when we extend
    #     this beyond NOVEL, that code will need to change
    query = text("""SELECT t.title_id, t.title_parent, t.title_title,
          CAST(t.title_copyright AS CHAR) t_copyright,
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
    return postprocess_bibliography(rows)


def postprocess_bibliography(raw_rows):
    title_id_to_titles = defaultdict(set)
    publication_dict = defaultdict(set)
    # TODO: might be nice to order the titles by most popular first?
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
    for i, (titles, pub_date) in enumerate(bibliography, 1):
        print('%2d. [%d] %s' % (i, pub_date.year, ' aka '.join(titles)))

