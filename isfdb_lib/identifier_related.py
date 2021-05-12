#!/usr/bin/env python3
"""
Functions for querying the database regarding the existence - or more often,
the absence - of book IDs e.g. ISBNs, ASINs, etc.

Generic functions related to IDs - i.e. ones that don't rely on a database
connection or are otherwise ISFDB-specific - should go in separate modules
such as isbn_functions.py
"""

from collections import namedtuple
import re


PubTitleAuthorStuff = namedtuple('PubTitleAuthorStuff',
                                 'pub_id, pub_title, title_id, title, '
                                 'format, pub_type, '
                                 'authors, identifiers')

ASIN_POSSIBLE_INITIAL_CHARACTERS = 'B' # presumably C etc will be added eventually?

from sqlalchemy.sql import text

from isbn_functions import isbn10and13

def check_asin(conn, asin):
    """
    Return True or False depending on if the provided ASIN or Audible-ASIN
    exists in ISFDB.

    No attempt is made to verify if the provided value is a valid ASIN, or
    if it is an ISBN-10 that Amazon has "repurposed" as an ASIN.
    """
    if not asin:
        return False
    query = text("""SELECT  * FROM identifiers i
    LEFT OUTER JOIN identifier_types it ON i.identifier_type_id = it.identifier_type_id
    WHERE it.identifier_type_name IN ('ASIN', 'Audible-ASIN')
    AND i.identifier_value = :asin;""")
    results = conn.execute(query, {'asin': asin}).fetchall()
    return len(results) > 0


def check_isbn(conn, raw_isbn, check_only_this_isbn=False):
    """
    Return True or False depending on if the provided ISBN exists in ISFDB.

    No attempt is made to verify if the provided value is a valid ISBN.  However,
    it will be normalized (e.g. remove any extraneous spaces or hyphens) and
    the both ISBN-10 and ISBN-13 variants of the same fundamental ISBN will be
    searched for.  Set check_only_this_isbn to True if you don't want the latter
    behaviour for some reason.
    """
    # ISBN13s are often of the form "978-....", so we normalize that out.
    # Note X can be the final character for ISBN-10s:
    # https://en.wikipedia.org/wiki/International_Standard_Book_Number#Check_digits
    isbn = re.sub('[^\dX]', '', raw_isbn.upper())
    if check_only_this_isbn:
        isbns = [isbn]
    else:
        isbns = isbn10and13(isbn)
    if not isbns:
        return False

    query = text("""SELECT  * FROM pubs WHERE pub_isbn in :isbns;""")
    results = conn.execute(query, {'isbns': isbns}).fetchall()
    return len(results) > 0


def _get_authors_and_title_for_identifiers(conn, identifiers,
                                           filters, extra_joins=None):
    """
    Return a PubTitleAuthorStuff for the given identifiers:
    If multiple pub_id/pub_titles match, only the first one found is used.

    filters should be a list of strings of the form
    "table.column_name IN :identifiers"

    extra_joins should (iff needed) be a list of strings of the form
    "LEFT OUTER JOIN tablename x ON x.some_id = y.some_id"

    It is assumed that the identifiers have had basic sanitization e.g.
    removal of hyphens or spaces in ISBNs, and that any variants that should
    be checked (e.g. ISBN-10 and ISBN-13 forms) are provided within identifiers)

    Returns None for no match
    """

    if not extra_joins:
        extra_joins = []
    joined_joins = '\n  '.join(extra_joins)

    if isinstance(filters, str):
        # Convenience in case we forget to pass a list
        filter = filters
    else:
        filter = ' AND '.join(filters)

    query = text(f"""SELECT p.pub_id, pub_title, t.title_id, t.title_title,
      p.pub_isbn, p.pub_ptype format, p.pub_ctype pub_type
    FROM pubs p
    LEFT OUTER JOIN pub_content pc ON pc.pub_id = p.pub_id
    LEFT OUTER JOIN titles t ON pc.title_id = t.title_id
    {joined_joins}
    WHERE p.pub_ctype = t.title_ttype AND {filter};""")
    results = conn.execute(query, {'identifiers': identifiers}).fetchall()

    if not results:
        return None

    r = results[0]
    ret = [r.pub_id, r.pub_title, r.title_id, r.title_title, r.format, r.pub_type]

    query = text("""SELECT a.author_id, author_canonical
    FROM canonical_author ca
    LEFT OUTER JOIN authors a ON a.author_id = ca.author_id
    WHERE ca.title_id = :title_id;""")
    results = conn.execute(query, {'title_id': ret[2]}).fetchall()
    author_stuff = [(z.author_id, z.author_canonical) for z in results]

    ret.append(author_stuff)
    ret.append([r.pub_isbn]) # A list, because TODO we need to add any ASIN as well
    return PubTitleAuthorStuff(*ret)


def get_authors_and_title_for_isbn(conn, raw_isbn, check_only_this_isbn=False):
    """
    Return a tuple/list of the following for the given ISBN:
    * pub_id    } Only the first one found, if there's more than one pub
    * pub_title } for this ISBN
    * title_id
    * title_title
    * A list of (author_id, author name)

    Or None for no match, invalid ISBNs, etc
    """

    isbn = re.sub('[^\dX]', '', raw_isbn.upper())
    if check_only_this_isbn:
        isbns = [isbn]
    else:
        isbns = isbn10and13(isbn)
    if not isbns:
        return None

    return _get_authors_and_title_for_identifiers(conn, isbns,
                                                  'p.pub_isbn IN :identifiers')


def get_authors_and_title_for_asin(conn, raw_asin):
    """
    Return a tuple/list of the following for the given ASIN:
    * pub_id    } Only the first one found, if there's more than one pub
    * pub_title } for this ASIN
    * title_id
    * title_title
    * A list of (author_id, author name)

    Or None for no match, invalid ASIN, etc

    IMPORTANT NOTE: This will not match ISBN-10s that Amazon uses as ASINs for
    (some?) physical books.
    """

    asin = re.sub('\W', '', raw_asin.upper())
    return _get_authors_and_title_for_identifiers(
        conn, [asin],
        ['i.identifier_value IN :identifiers',
         "it.identifier_type_name IN ('ASIN', 'Audible-ASIN')"],
        ['LEFT OUTER JOIN identifiers i ON i.pub_id = p.pub_id',
         'LEFT OUTER JOIN identifier_types it ON i.identifier_type_id = it.identifier_type_id'])



if __name__ == '__main__':
    import sys
    from common import (get_connection)
    conn = get_connection()

    for i, identifier in enumerate(sys.argv[1:]):
        if i > 0:
            print()
        if identifier[0] in ASIN_POSSIBLE_INITIAL_CHARACTERS:
            print(get_authors_and_title_for_asin(conn, identifier))
        else:
            print(get_authors_and_title_for_isbn(conn, identifier))


