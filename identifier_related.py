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
                                 'pub_id, pub_title, title_id, title, authors')

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

    query = text("""SELECT p.pub_id, pub_title, t.title_id, t.title_title
    FROM pubs p
    LEFT OUTER JOIN pub_content pc ON pc.pub_id = p.pub_id
    LEFT OUTER JOIN titles t ON pc.title_id = t.title_id
    WHERE p.pub_isbn in :isbns;""")
    results = conn.execute(query, {'isbns': isbns}).fetchall()

    if not results:
        return None

    r = results[0]
    ret = [r.pub_id, r.pub_title, r.title_id, r.title_title]

    query = text("""SELECT a.author_id, author_canonical
    FROM canonical_author ca
    LEFT OUTER JOIN authors a ON a.author_id = ca.author_id
    WHERE ca.title_id = :title_id;""")
    results = conn.execute(query, {'title_id': ret[2]}).fetchall()
    author_stuff = [(z.author_id, z.author_canonical) for z in results]

    ret.append(author_stuff)
    return PubTitleAuthorStuff(*ret)

if __name__ == '__main__':
    import sys
    from common import (get_connection)
    conn = get_connection()

    for i, isbn in enumerate(sys.argv[1:]):
        if i > 0:
            print()
        print(get_authors_and_title_for_isbn(conn, isbn))


