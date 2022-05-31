#!/usr/bin/env python3
"""
Note: These tests rely on the database, as some of the tested functions are
essentially SQL queries with a bit of tweaking in Python.
"""

from datetime import date
import unittest

from sqlalchemy.exc import OperationalError

from ..common import (get_connection, parse_args)
from ..title_related import (get_title_details_from_id,
                             get_title_ids,
                             get_all_related_title_ids,
                             fetch_title_details,
                             get_authors_for_title,
                             get_definitive_authors)
from ..author_aliases import AuthorIdAndName


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




class TestGetAllRelatedTitleIds(unittest.TestCase):
    conn = get_connection()

    wdd_ids = [WAYDOWNDARK_CHILD_DETAILS[0], WAYDOWNDARK_PARENT_DETAILS[0]]

    def test_wdd_child_from_child(self):
        self.assertEqual(self.wdd_ids,
                         get_all_related_title_ids(self.conn, self.wdd_ids[0]))

    def test_wdd_child_from_parent(self):
        self.assertEqual(self.wdd_ids,
                         get_all_related_title_ids(self.conn, self.wdd_ids[1]))


    # Following tests use T. J. Bass - Half Past Human
    def test_all_languages_from_english_parent(self):
        self.assertEqual([1823, 1471985, 1499455],
                         sorted(get_all_related_title_ids(self.conn, 1823,
                                                   only_same_languages=False)))

    def test_same_language_only_from_english_parent(self):
        self.assertEqual([1823],
                         get_all_related_title_ids(self.conn, 1823,
                                                   only_same_languages=True))

    def test_all_languages_from_translated_child(self):
        self.assertEqual([1823, 1471985, 1499455],
                         sorted(get_all_related_title_ids(self.conn, 1499455,
                                                   only_same_languages=False)))

    def test_same_language_only_from_translated_child(self):
        self.assertEqual([1499455],
                         get_all_related_title_ids(self.conn, 1499455,
                                                   only_same_languages=True))



class MockBook(object):
    def __init__(self, title_id, author):
        self.title_id = title_id
        self.author = author

class TestGetDefinitiveAuthors(unittest.TestCase):
    conn = get_connection()

    def test_true_author_found_when_pseudonym_credited(self):
        # Compare to TestGetAuthorsForTitle.test_credited_pseudonumous_author_found
        book = MockBook(2515634, 'Mira Grant') # Alien Echo as credited to Mira Grant
        self.assertEqual([AuthorIdAndName(129348, 'Seanan McGuire')],
                          get_definitive_authors(self.conn, book))

    def test_true_authors_found_when_joint_pseudonym_credited(self):
        # Compare to TestGetAuthorsForTitle.test_credited_joint_pseudonymous_author_found
        book = MockBook(21043, 'Gabriel King') # The Knot Garden
        self.assertEqual([AuthorIdAndName(1277, 'M. John Harrison'),
                          AuthorIdAndName(3665, 'Jane Johnson')],
                          sorted(get_definitive_authors(self.conn, book)))


class TestGetAuthorsForTitle(unittest.TestCase):
    conn = get_connection()

    # FYI "Alien Echo" is credited to different authors depending on edition/variant
    # http://www.isfdb.org/cgi-bin/title.cgi?2515634 - Mira Grant
    # http://www.isfdb.org/cgi-bin/title.cgi?2515635 - Seanan McGuire

    def test_credited_pseudonymous_author_found(self):
        self.assertEqual([AuthorIdAndName(133814, 'Mira Grant')],
                          get_authors_for_title(self.conn, 2515634))

    def test_credited_real_author_found(self):
        self.assertEqual([AuthorIdAndName(129348, 'Seanan McGuire')],
                          get_authors_for_title(self.conn, 2515635))


    # Gabriel King is really M. John Harrison & Jane Johnson - see earlier tests
    def test_credited_joint_pseudonymous_author_found(self):
        self.assertEqual([AuthorIdAndName(3664, 'Gabriel King')],
                          get_authors_for_title(self.conn, 21043))

    def test_credited_real_credited_author_found_not_pseudonym(self):
        # See issue #15, which probably isn't relevant here, but seems reasonable
        # to use as a test case
        self.assertEqual([AuthorIdAndName(3161, 'Paul Witcover')],
                          get_authors_for_title(self.conn, 8616))

