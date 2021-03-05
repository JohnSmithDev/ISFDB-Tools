#!/usr/bin/env python3
"""
Note: These tests rely on the database, as some of the tested functions are
essentially SQL queries with a bit of tweaking in Python.
"""

import unittest

from ..common import get_connection
from ..author_aliases import (unlegalize, get_author_aliases,
                              get_author_alias_ids, get_real_author_id,
                              get_real_author_id_and_name, get_gestalt_ids)

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
        self.assertEqual(['Seanan McGuire', 'Mira Grant', 'A. Deborah Baker'],
                         get_author_aliases(self.conn, 'Seanan McGuire'))

    def test_get_aliases_for_pseudonym_default_behaviour(self):
        self.assertEqual(['Mira Grant', 'Seanan McGuire', 'A. Deborah Baker'],
                         get_author_aliases(self.conn, 'Mira Grant'))

    def test_get_aliases_for_pseudonym_no_extra_lookup(self):
        self.assertEqual(['Mira Grant', 'Seanan McGuire'],
                         get_author_aliases(self.conn, 'Mira Grant',
                                            search_for_additional_pseudonyms=False))

    # These next two tests show an inconsistency - if we put in a pseudonym,
    # we don't get any other pseudonyms back.  TODO: fix this if it becomes
    # an issue (it's been an issue for the Seanan McGuire aliases)
    def test_get_aliases_for_joint_pseudonym(self):
        self.assertEqual(['James S. A. Corey',
                          'Tyler Corey Franck',
                          'Daniel Abraham',
                          'Ty Franck'],
                         get_author_aliases(self.conn, 'James S. A. Corey',
                                            search_for_additional_pseudonyms=False))


    def test_get_aliases_for_real_name_using_joint_pseudonym(self):
        # The returned list is ordered by "similarity", although this is a
        # somewhat nebulous concept and shouldn't be relied on in production code
        self.assertEqual(['Daniel Abraham',
                          'Daniel Hanover',
                          'James Corey',
                          'James S. A. Corey',
                          'M. L. N. Hanover',
                          # The following were added to the DB whilst I was
                          # being too idle to run & update the tests :-(
                          'D\x9eejms S. A. Kori', # 319366
                          # Note next string is split over 2 lines
                          '&#1044;&#1078;&#1077;&#1081;&#1084;&#1089; '
                          '&#1050;&#1086;&#1088;&#1080;',
                          # Note next string is split over 2 lines
                          '&#1044;&#1078;&#1077;&#1081;&#1084;&#1089; &#1057;. &#1040;. '
                          '&#1050;&#1086;&#1088;&#1080;' # 319390
                          ],
                         get_author_aliases(self.conn, 'Daniel Abraham',
                                            search_for_additional_pseudonyms=False))

    def test_numeric_author_id_argument(self):
        self.assertEqual(['A. A. Anderson', 'Andrew A. Anderson'],
                         get_author_aliases(self.conn, 162343))

class TestGetGestaltIds(unittest.TestCase):
    conn = get_connection()

    HOLDSTOCKS = [1024, 14689, 114231, 93937, 2584, 2586, 308265,
                  256642, 2585, 2583, 2559, 114794]

    def test_get_gestalt_ids(self):
        self.assertEqual([2559],
                         get_gestalt_ids(self.conn, self.HOLDSTOCKS, 2))

    def test_get_gestalt_ids_not_enough(self):
        self.assertEqual([],
                         get_gestalt_ids(self.conn, self.HOLDSTOCKS, 99))

class TestGetAuthorAliasIds(unittest.TestCase):
    conn = get_connection()

    def test_get_alias_ids_for_real_name(self):
        self.assertEqual([129348, 133814, 317644],
                         get_author_alias_ids(self.conn, 'Seanan McGuire'))

    def test_get_alias_ids_for_pseudonym1_default_behaviour(self):
        # Mira Grant ID should precede Seanan McGuire & A. Deborah Baker IDs
        # The order of the 2nd and 3rd names/IDs is fairly arbitrary, so if the
        # algorithm ever changes, it'll be OK to swap those values around in
        # this test
        self.assertEqual([133814,
                          129348,
                          317644],
                         get_author_alias_ids(self.conn, 'Mira Grant'))

    def test_get_alias_ids_for_pseudonym2_default_behaviour(self):
        # A. Deborah Baker ID should precede Seanan McGuire & Mira Grant IDs
        # The order of the 2nd and 3rd names/IDs is fairly arbitrary, so if the
        # algorithm ever changes, it'll be OK to swap those values around in
        # this test
        self.assertEqual([317644,
                          133814,
                          129348],
                         get_author_alias_ids(self.conn, 'A. Deborah Baker'))

    def test_get_alias_ids_for_pseudonym1_no_extra_lookup(self):
        # Mira Grant ID should precede Seanan McGuire ID
        self.assertEqual([133814,
                          129348],
                         get_author_alias_ids(self.conn, 'Mira Grant',
                                              search_for_additional_pseudonyms=False))

    def test_get_alias_ids_for_pseudonym2_no_extra_lookup(self):
        # A. Deborah Baker ID should precede Seanan McGuire ID
        self.assertEqual([317644,
                          129348],
                         get_author_alias_ids(self.conn, 'A. Deborah Baker',
                                              search_for_additional_pseudonyms=False))


    def test_get_alias_ids_excluding_gestalts(self):
        # Excludes "Richard Kirk" (id 2559), used by 3 authors inc. Holdstock
        self.assertEqual([1024, 14689, 114231, 93937, 2584, 2586, 308265,
                          256642, 2585, 2583, 114794],
                         get_author_alias_ids(self.conn, 'Robert Holdstock', 2))

    def test_get_alias_ids_including_gestalts(self):
        self.assertEqual([1024, 14689, 114231, 93937, 2584, 2586, 308265,
                          256642, 2585, 2583, 2559, 114794],
                         get_author_alias_ids(self.conn, 'Robert Holdstock', 99))


class TestGetRealAuthorId(unittest.TestCase):

    conn = get_connection()

    def test_simple_real_name(self):
        self.assertEqual([129348], # SMcG
                         get_real_author_id(self.conn, 133814)) #MG

    def test_already_real_name(self):
        self.assertEqual(None,
                         get_real_author_id(self.conn, 129348)) # SMcG

    def test_multiple_real_name(self):
        self.assertEqual([10297, 123977], # DA, TF
                         get_real_author_id(self.conn, 155601)) # JSAC

class TestGetRealAuthorIdAndName(unittest.TestCase):

    conn = get_connection()

    def test_simple_real_name(self):
        self.assertEqual([(129348, 'Seanan McGuire')],
                         get_real_author_id_and_name(self.conn, 133814)) #MG

    def test_already_real_name(self):
        self.assertEqual(None,
                         get_real_author_id_and_name(self.conn, 129348)) # SMcG

    def test_multiple_real_name(self):
        self.assertEqual([(10297, 'Daniel Abraham'), (123977, 'Ty Franck')],
                         get_real_author_id_and_name(self.conn, 155601)) # JSAC
