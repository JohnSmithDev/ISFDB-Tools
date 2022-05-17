#!/usr/bin/env python3
"""
Note: These tests rely on the database, as some of the tested functions are
essentially SQL queries with a bit of tweaking in Python.
"""

from datetime import date
import unittest

from sqlalchemy.exc import OperationalError

from ..common import (get_connection, parse_args)
#from ..publication_history import (get_publications_by_country,
# PublicationDetails)
from ..identifier_related import (PubTitleAuthorStuff,
                                  get_authors_and_title_for_isbn,
                                  get_authors_and_title_for_asin)



class TestGetAuthorsAndTitleForISBN(unittest.TestCase):
    conn = get_connection()

    def test_simple_match_for_isbn(self):
        ret = get_authors_and_title_for_isbn(self.conn, '9781473233058',
                                             both_isbn10_and_isbn13=False)
        self.assertEqual(PubTitleAuthorStuff(pub_id=834078,
                                             pub_title='The Separation',
                                             title_id=23363,
                                             title='The Separation',
                                             format='tp',
                                             pub_type='NOVEL',
                                             authors=[(336, 'Christopher Priest')],
                                             identifiers=['9781473233058']),
                         ret)

    def test_simple_failure_to_match(self):
        ret = get_authors_and_title_for_isbn(self.conn, '9781473233000')
        self.assertEqual(None, ret)


class TestGetAuthorsAndTitleForASIN(unittest.TestCase):
    conn = get_connection()

    def test_simple_match(self):
        # Note that the current implementation (and thus what we test) is
        # arguably sub-optimal/counter-intuitive: the identifiers property is
        # a list that currently only returns the ISBN, it should really include
        # the ASIN (and any other identifiers)
        ret = get_authors_and_title_for_asin(self.conn, 'B005LWQCJ0',
                                             both_isbn10_and_isbn13=False)
        self.assertEqual(PubTitleAuthorStuff(pub_id=447773,
                                             pub_title='The Separation',
                                             title_id=23363,
                                             title='The Separation',
                                             format='ebook',
                                             pub_type='NOVEL',
                                             authors=[(336, 'Christopher Priest')],
                                             identifiers=['9780575114951']),
                         ret)

    def test_simple_failure_to_match(self):
        ret = get_authors_and_title_for_asin(self.conn, 'B005LWQZZZ')
        self.assertEqual(None, ret)
