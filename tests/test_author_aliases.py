#!/usr/bin/env python3
"""
Note: These tests rely on the database, as some of the tested functions are
essentially SQL queries with a bit of tweaking in Python.
"""

import unittest

from ..common import get_connection
from ..author_aliases import (unlegalize, get_author_aliases,
                              get_author_alias_ids)

class TestUnlegalize(unittest.TestCase):
    def test_none(self):
        self.assertIsNone(unlegalize(None))
    def test_empty(self):
        self.assertEqual('', unlegalize(''))

    def test_no_comma(self):
        # Perhaps these are wrong in ISFDB?  At any rate, make sure we don't
        # blow up on them
        # Examples: Joseph Rubas, Anthony Shillitoe, Brian M. White etc
        self.assertEqual('Bert Gentry Lee', unlegalize('Bert Gentry Lee'))

    def test_one_comma(self):
        self.assertEqual('Clark Ashton Smith', unlegalize('Smith, Clark Ashton'))

    def test_one_comma_stripping(self):
        self.assertEqual('Clark Ashton Smith', unlegalize('  Smith     ,  Clark Ashton   '))

    def test_two_commas(self):
        self.assertEqual('John Wood Campbell Jr.', unlegalize('Campbell, John Wood, Jr.'))
        self.assertEqual('Andrew Jefferson Offutt V', unlegalize('Offutt, Andrew Jefferson, V'))
        self.assertEqual('Gerald Allan Sohl Sr.', unlegalize('Sohl, Gerald Allan, Sr.'))

        """
        Here are some that aren't currently supported properly, TODO: add them
        in when they are:
        Plunkett, Edward John Moreton Drax, 18th Baron Dunsany
        Erckmann, Émile (left) + Chatrian, Alexandre (right)
        Van der Poel, Jr., Washington Irving
        Dumas, Alexandre, père (Sr.)
        """

    def test_three_or_more_commas(self):
        """
        There are only three of these as of April 2019:

        select author_id,  author_legalname from authors where author_legalname like '%,%,%,%';
        +-----------+---------------------------------------------------------------------------+
        | author_id | author_legalname                                                          |
        +-----------+---------------------------------------------------------------------------+
        |    166246 | Mackworth, Harry Llewellyn, 8th Baronet Mackworth of the Gnoll, Glamorgan |
        |    205352 | Mosley, Nicholas, 3rd Baron Ravensdale, 7th Baronet                       |
        |    209269 | Medous, Jean André [then Lévy, Jean-André, in 1910]                       |
        +-----------+---------------------------------------------------------------------------+
        3 rows in set (0.08 sec)

        As such, I'm not going to worry about them for now
        """
        pass

        # self.assertEqual('', unlegalize(''))


class TestGetAuthorAliases(unittest.TestCase):

    conn = get_connection()

    # Tip: As this depends on the database, prefer to use deceased authors who
    # are (relatively)  unlikely to acquire new aliases.  (Although as yet
    # I'm not doing that, instead using examples that are well known and thus
    # easy to see what the expected result should be.)
    def test_get_aliases_for_real_name(self):
        self.assertEqual(set(['Mira Grant', 'Seanan McGuire']),
                         get_author_aliases(self.conn, 'Seanan McGuire'))

    def test_get_aliases_for_pseudonym(self):
        self.assertEqual(set(['Mira Grant', 'Seanan McGuire']),
                         get_author_aliases(self.conn, 'Mira Grant'))

    # These next two tests show an inconsistency - if we put in a pseudonym,
    # we don't get any other pseudonyms back.  TODO: fix this if it becomes
    # an issue
    def test_get_aliases_for_joint_pseudonym(self):
        self.assertEqual(set(['Daniel Abraham', 'James S. A. Corey',
                              'Ty Franck', 'Tyler Corey Franck']),
                         get_author_aliases(self.conn, 'James S. A. Corey'))
    def test_get_aliases_for_real_name_usingjoint_pseudonym(self):
        self.assertEqual(set(['Daniel Abraham', 'James S. A. Corey',
                              'James Corey', 'M. L. N. Hanover', 'Daniel Hanover']),
                         get_author_aliases(self.conn, 'Daniel Abraham'))





class TestGetAuthorAliasIds(unittest.TestCase):
    conn = get_connection()

    def test_get_alias_ids_for_real_name(self):
        self.assertEqual([129348, 133814],
                         get_author_alias_ids(self.conn, 'Seanan McGuire'))

    def test_get_alias_ids_for_real_name(self):
        self.assertEqual([129348, 133814],
                         get_author_alias_ids(self.conn, 'Mira Grant'))
