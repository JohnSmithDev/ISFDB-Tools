#!/usr/bin/env python3
"""
Note: These tests rely on the database, as some of the tested functions are
essentially SQL queries with a bit of tweaking in Python.
"""

from datetime import date
import unittest

from sqlalchemy.exc import OperationalError

from ..common import (get_connection, parse_args)
from ..publication_history import (get_title_details_from_id,
                                   get_title_ids,
                                   get_all_related_title_ids,
                                   get_publications,
                                   fetch_title_details)


REVENGER_DETAILS = (2034339, 'Alastair Reynolds', 'Revenger', 0)
WAYDOWNDARK_CHILD_DETAILS = (1866037, 'J. P. Smythe', 'Way Down Dark', 1866038)
WAYDOWNDARK_PARENT_DETAILS = (1866038, 'James Smythe', 'Way Down Dark', 0)

class TestGetTitleDetailsFromId(unittest.TestCase):
    conn = get_connection()

    GIRL_GIFTS_DETAILS = (1769307, 'Mike Carey', 'The Girl with All the Gifts', 0)

    def test_existing_basic(self):
        self.assertEqual(REVENGER_DETAILS,
                         get_title_details_from_id(self.conn, 2034339))

    def test_existing_extra_columns(self):
        val = REVENGER_DETAILS + (date(2016,9,7), date(1966,3,13))
        self.assertEqual(val,
                         get_title_details_from_id(self.conn, 2034339,
                                                   extra_columns=['title_copyright',
                                                                  'author_birthdate']))

    def test_bad_extra_columns(self):
        val = REVENGER_DETAILS + (date(2016,9,7), date(1966,3,13))
        with self.assertRaises(OperationalError):
            get_title_details_from_id(self.conn, 2034339,
                                      extra_columns=['thisdoesntexist'])

    def test_existing_parent(self):
        self.assertEqual(self.GIRL_GIFTS_DETAILS,
                         get_title_details_from_id(self.conn, 1769307))

    def test_existing_child_no_parent_lookup(self):
        self.assertEqual(None,
                         get_title_details_from_id(self.conn, 16666651, parent_search_depth=0))

    def test_existing_child_with_parent_lookup(self):
        self.assertEqual(self.GIRL_GIFTS_DETAILS,
                         get_title_details_from_id(self.conn, 1666651, parent_search_depth=1))


class TestFetchTitleDetails(unittest.TestCase):
    conn = get_connection()

    def test_existing_basic(self):
        self.assertEqual([REVENGER_DETAILS],
                         fetch_title_details(self.conn,
                                             'title_title = :title AND author_canonical = :author',
                                           {'title': 'Revenger',
                                            'author': 'Alastair Reynolds',
                                            'title_types': ['NOVEL']},
                                           extra_col_str=''))

    def test_existing_basic_title_only(self):
        self.assertEqual([REVENGER_DETAILS],
                         fetch_title_details(self.conn, 'title_title = :title',
                                           {'title': 'Revenger',
                                            'title_types': ['NOVEL']},
                                           extra_col_str=''))

    def test_no_match(self):
        self.assertEqual([],
                         fetch_title_details(self.conn,
                                             'title_title = :title AND author_canonical = :author',
                                           {'title': 'This Book Does Not Exist',
                                            'author': 'John Doe',
                                            'title_types': ['NOVEL']},
                                           extra_col_str=''))

    def test_parent_issue_1(self):
        self.assertEqual([WAYDOWNDARK_CHILD_DETAILS, WAYDOWNDARK_PARENT_DETAILS],
                         fetch_title_details(self.conn, 'title_title = :title',
                                           {'title': 'Way Down Dark',
                                            'author': 'J. P. Smythe',
                                            'title_types': ['NOVEL']},
                                           extra_col_str=''))

    def test_parent_issue_2(self):
        self.assertEqual([WAYDOWNDARK_CHILD_DETAILS, WAYDOWNDARK_PARENT_DETAILS],
                        fetch_title_details(self.conn, 'title_title = :title',
                                           {'title': 'Way Down Dark',
                                            'author': 'James Smythe',
                                            'title_types': ['NOVEL']},
                                           extra_col_str=''))

class TestGetTitleIds(unittest.TestCase):
    conn = get_connection()

    def test_wdd_child(self):
        wdd_ids = [WAYDOWNDARK_PARENT_DETAILS[0], WAYDOWNDARK_CHILD_DETAILS[0]]
        args = parse_args(['-A', 'J. P. Smythe', '-T', 'Way Down Dark'],
                          description='whatever')
        self.assertEqual(sorted(wdd_ids),
                         get_title_ids(self.conn, args))

    def test_wdd_parent(self):
        wdd_ids = [WAYDOWNDARK_PARENT_DETAILS[0], WAYDOWNDARK_CHILD_DETAILS[0]]
        args = parse_args(['-A', 'James Smythe', '-T', 'Way Down Dark'],
                          description='whatever')
        self.assertEqual(sorted(wdd_ids),
                         get_title_ids(self.conn, args))


class TestGetPublications(unittest.TestCase):
    conn = get_connection()

    def test_wdd(self):
        wdd_ids = [WAYDOWNDARK_CHILD_DETAILS[0], WAYDOWNDARK_PARENT_DETAILS[0]]
        ret = get_publications(self.conn, wdd_ids)
        print(ret)
        # See http://www.isfdb.org/cgi-bin/title.cgi?1866037
        # and http://www.isfdb.org/cgi-bin/title.cgi?1866038
        self.assertEqual({'GB': [('tp', date(2015, 7, 2), '9781444796322'),
                                 ('tp', date(2016, 4, 7), '9781444796339')],
                          'US': [('hc', date(2016, 10, 4), '9781681443850'),
                                 ('ebook', date(2016, 10, 4), '9781681443836'),
                                 ('tp', date(2017, 10, 3), '9781681443843')]},
                         ret)


class TestGetAllrelatedTitleIds(unittest.TestCase):
    conn = get_connection()

    def test_wdd_child(self):
        wdd_ids = [WAYDOWNDARK_CHILD_DETAILS[0], WAYDOWNDARK_PARENT_DETAILS[0]]
        self.assertEqual(wdd_ids, get_all_related_title_ids(self.conn, wdd_ids[0]))

    def test_wdd_child(self):
        wdd_ids = [WAYDOWNDARK_CHILD_DETAILS[0], WAYDOWNDARK_PARENT_DETAILS[0]]
        self.assertEqual(wdd_ids, get_all_related_title_ids(self.conn, wdd_ids[1]))
