#!/usr/bin/env python3
"""
Return/output biographical details about an author.

This is fairly useless as a standalone script, but may be convenient as part
of a bigger report/project.
"""


from collections import defaultdict, Counter, namedtuple
from datetime import date
from functools import reduce, lru_cache
from itertools import chain
import logging
import pdb
import sys


from sqlalchemy.sql import text

from common import (get_connection, create_parser, parse_args,
                    AmbiguousArgumentsError)
from isfdb_utils import (convert_dateish_to_date, safe_year_from_date)
# from author_aliases import get_author_alias_ids
# from deduplicate import (DuplicatedOrMergedRecordError,
#                         make_list_excluding_duplicates)
# from publisher_variants import REVERSE_PUBLISHER_VARIANTS


def get_author_bio(conn, exact_author):
    query = text("""SELECT *,
      CAST(author_birthdate AS CHAR) birthdate_ish,
      CAST(author_deathdate AS CHAR) deathdate_ish
FROM authors a
WHERE author_canonical = :exact_author;
""")
    row = conn.execute(query, {'exact_author': exact_author}).fetchone()
    ret = dict(zip(row.keys(), row.values()))
    # Add some conveniences
    ret.update({
        'name': ret['author_canonical'],
        'birth_year': safe_year_from_date(convert_dateish_to_date(ret['birthdate_ish'])),
        'death_year': safe_year_from_date(convert_dateish_to_date(ret['deathdate_ish']))
        })

    return ret

def name_with_dates(bio):
    """
    Given a bio dict (as returned from get_author_bio) return a string
    of form "Joe Bloggs (1950-)"
    """
    return '%s (%s-%s)' % (bio['name'],
                           bio['birth_year'] or '?',
                           bio['death_year'] or '')


if __name__ == '__main__':
    conn = get_connection()

    for exact_author in sys.argv[1:]:
        details = get_author_bio(conn, exact_author)
        print(name_with_dates(details))


