#!/usr/bin/env python3
"""
These tests are naughty, as they will download Wikipedia or Twitter URLs (in the
event we don't have those pages cached already).
TODO: mocking of that functionality
"""

import unittest

from ..common import (get_connection, parse_args)
from ..author_gender import get_author_gender

# Note on terminology:
# "in_isfdb" means there is a record in the authors table.
# There are a number of people who have records in the awards table but not
# authors, and in this context they are considered "not_in_isfdb"


class TestDeriveGenderFromPronouns(unittest.TestCase):

    conn = get_connection()

    def test_male_in_isfdb_and_wikipedia(self):
        gender, detail = get_author_gender(self.conn, ['Alastair Reynolds'])
        self.assertEqual('M', gender)
        self.assertEqual('wikipedia', detail.split(':')[0])

    def test_male_in_isfdb_and_twitter_but_not_wikipedia(self):
        # This test is massively flakey (until we get proper mocking in place)
        gender, detail = get_author_gender(self.conn, ['Dominik Parisien'])
        self.assertEqual('M', gender)
        self.assertEqual('twitter', detail.split(':')[0])

    def test_male_in_isfdb_not_in_wikipedia_or_twitter_but_with_recognized_name(self):
        # This test is massively flakey (until we get proper mocking in place)
        gender, detail = get_author_gender(self.conn, ['Robert Stallman'])
        self.assertEqual('M', gender)
        self.assertEqual('human-names', detail)

    def test_male_not_in_isfdb_not_in_wikipedia_or_twitter_but_with_recognized_name(self):
        # This test is massively flakey (until we get proper mocking in place)
        gender, detail = get_author_gender(self.conn, ['Douglas Blargleburt'])
        self.assertEqual('M', gender)
        self.assertEqual('human-names', detail)

    def test_unknown_not_in_isfdb_or_wikipedia_or_twitter_and_unknown_name(self):
        # This test is massively flakey (until we get proper mocking in place)
        gender, detail = get_author_gender(self.conn, ['Urglefrod Smith'])
        self.assertIsNone(gender)

    def test_initialized_author_no_links_but_gendered_legalname(self):
        #  "A. A. Anderson" (author_id=162343) is not in Wikipedia or Twitter
        # However their legalname is defined, so we should be able to use
        # that in conjunction with human-names
        gender, detail = get_author_gender(self.conn, ['A. A. Anderson'])
        self.assertEqual('M', gender)
        # It's possible this second check might fail, if/when they get a Wikipedia
        # page or gendered Twitter bio.  In such a case, you'll have to find
        # another example in the database :-(
        # IIRC, the name is included after human-names: to indicate that it
        # was a derived name
        self.assertEqual('human-names:Andrew A. Anderson', detail)


