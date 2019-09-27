#!/usr/bin/env python3
"""
Find a book given the author name and title.

This is intended to be flexible and able to cater for discrepancies e.g.

* name variations like "N. K. Jemisin" vs "NK Jemisin" vs "Nora K. Jemisin"
* title variations like "Rejoice" vs "Rejoice - A Knife to the Heart"

Although it works standalone, it's intended more for stuff like programmatically
looking up Goodreads books where names/titles might not match exactly.

"""


from collections import defaultdict, namedtuple
from datetime import datetime
# from functools import reduce, lru_cache
import pdb
import sys

from sqlalchemy.sql import text

from common import (get_connection, parse_args, AmbiguousArgumentsError)
from author_aliases import (get_author_alias_ids)
from title_related import get_title_details

class BookNotFoundError(Exception):
    pass

AuthorAndTitleIds = namedtuple('AuthorAndTitleIds', 'author_id, title_id')


def find_book_for_author_and_title(conn, author, title):
    """
    Return a list of tuple of (author_id, title_id) for matching book(s).

    TODO: optional filtering for certain types of title
    """

    # Q: How much does this replicate discover_title_details() in title_related?

    alias_ids = set(get_author_alias_ids(conn, author))

    # Get title IDs.
    title_filter_args = parse_args(['-T', title], description='whatever')
    title_list = get_title_details(conn, title_filter_args,
                                   extra_columns=['a.author_id'])

    if alias_ids and title_list:
        ret = []
        for tstuff in title_list:
            if tstuff.author_id in alias_ids:
                ret.append(AuthorAndTitleIds(tstuff.author_id, tstuff.title_id))
        if ret:
            return ret

    ### Following stuff is TODO

    # Else if no title IDs, get a list of all the titles associated with the
    # author.  Return any that have title match over a Levenstein ish threshold

    # If we have title IDs, but no author IDs, get a list of author names
    # for those titles.  If any author match over a Levenstein ish threshold,
    # return those.

    # If neither match - give up?
    raise BookNotFoundError('No book found for author %s/title %s' % (author, title))


if __name__ == '__main__':
    conn = get_connection()

    # ret = find_book_for_author_and_title(conn, 'Alastair Reynolds', 'Revenger')
    # print(ret)

    ret = find_book_for_author_and_title(conn, 'N. K. Jemisin', 'The Fifth Season')
    print(ret)

    ret = find_book_for_author_and_title(conn, 'C.L. Moore', 'Doomsday Morning')
    # ISFDB has "C. L. Moore"
    print(ret)
