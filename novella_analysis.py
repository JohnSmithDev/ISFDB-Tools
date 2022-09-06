#!/usr/bin/env python3
"""
Report interesting (?) stats about novellas.

This may focus on just novellas published as standalone CHAPBOOKs, or any
format (e.g. magazine, collection) - see how things develop...

Will probably focus on new, adult, genre, English novellas only, at least
at first
"""


from collections import defaultdict, Counter, namedtuple
from functools import reduce, lru_cache
import logging
import pdb
import sys


from sqlalchemy.sql import text

from common import (get_connection, parse_args, AmbiguousArgumentsError,
                    get_filters_and_params_from_args)
from isfdb_utils import (convert_dateish_to_date, merge_similar_titles)
from author_aliases import get_author_alias_ids
from deduplicate import (DuplicatedOrMergedRecordError,
                         make_list_excluding_duplicates)

# See language table, titles.title_language
VALID_LANGUAGE_IDS = [17]

# DEFAULT_TITLE_TYPES = ['CHAPBOOK']

STORY_LENGTH = 'novella' # column titles.title_storylen
PUB_FORMATS = ['ebook', 'hc', 'tp', 'pb']


def get_novellas(conn, args):
    fltr, params = get_filters_and_params_from_args(
        args, column_name_mappings={'year': 'title_copyright'})

    # TODO: handling of 'vague' dates that Python date object doesn't like
    query = text('''
SELECT *
FROM titles t
LEFT OUTER JOIN pub_content pc ON pc.title_id = t.title_id
LEFT OUTER JOIN pubs p ON pc.pub_id = p.pub_id
LEFT OUTER JOIN publishers pb ON p.publisher_id = pb.publisher_id
WHERE t.title_storylen = :story_length
  AND t.title_non_genre = 'No' AND t.title_graphic = 'No'
  AND t.title_nvz = 'No' AND t.title_jvn = 'No'
  AND t.title_language IN :languages
  AND p.pub_ptype IN :pub_formats
  AND YEAR(p.pub_year) = YEAR(t.title_copyright) -- avoid reprints
  AND %s
ORDER BY t.title_id, t.title_copyright;
''' % (fltr))

    params['story_length'] = STORY_LENGTH
    params['pub_formats'] = PUB_FORMATS
    params['languages'] = VALID_LANGUAGE_IDS


    results = conn.execute(query, **params).fetchall()
    return results

def postprocess_novellas(novellas):
    """
    Return a list of novellas that:
    * Collapses all the different pubs into a {publisher>list-of-formats} dict
    * Maybe does something with multiple authors?
    Presumes the novellas are sorted by title_id
    """
    title_id_to_details = {}
    for novella in novellas:
        title_id = novella['title_id']
        publisher = novella['publisher_name']
        fmt = novella['pub_ptype']
        pub_date = novella['pub_year']
        pub_type = novella['pub_ctype'] # CHAPBOOK, ANTHOLOGY, etc
        # ISBN is no good for ebooks (and audio, mags etc) but may be good for
        # identifying trad publishers vs (some?) indies?
        pub_isbn = novella['pub_isbn']
        pub_id = novella['pub_id']
        pub_details = (fmt, pub_date, pub_type, pub_id, pub_isbn)
        try:
            val = title_id_to_details[title_id]

        except KeyError:
            # val = dict(novella)
            # val['pubs'] = defaultdict(list)
            val = {
                'title_id': title_id,
                'title': novella['title_title'],
                'copyright_date': novella['title_copyright'],
                'pubs': defaultdict(list)
            }
            title_id_to_details[title_id] = val
        val['pubs'][publisher].append(pub_details)

    return title_id_to_details.values()

if __name__ == '__main__':
    args = parse_args(sys.argv[1:],
                      description='Report on novellas',
                      supported_args='py')

    conn = get_connection()

    novella_pubs = get_novellas(conn, args)
    novellas = postprocess_novellas(novella_pubs)
    for i, novella in enumerate(novellas, 1):
        print(f'{i}. {novella}')


