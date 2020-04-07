#!/usr/bin/env python3
"""
Functions for querying the database regarding the existence - or more often,
the absence - of book IDs e.g. ISBNs, ASINs, etc.

Generic functions related to IDs - i.e. ones that don't rely on a database
connection or are otherwise ISFDB-specific - should go in separate modules
such as isbn_functions.py
"""

import re

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
