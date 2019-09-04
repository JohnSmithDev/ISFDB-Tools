#!/usr/bin/env python3

import unittest

from ..twitter_bio import derive_gender_from_pronouns

class TestDeriveGenderFromPronouns(unittest.TestCase):

    def test_male_heslashhim(self):
        self.assertEqual('M', derive_gender_from_pronouns('Blah blah.  He/him'))

    def test_male_himinparens(self):
        self.assertEqual('M', derive_gender_from_pronouns('Blah blah.  (Him)'))


    def test_female_sheslashher1(self):
        self.assertEqual('F', derive_gender_from_pronouns('Blah blah.  She/her'))

    def test_female_sheslashher2(self):
        self.assertEqual('F', derive_gender_from_pronouns('Blah blah.  (She/her.)'))


    def test_nonbinary_oneword(self):
        self.assertEqual('X', derive_gender_from_pronouns('Blah blah.  Nonbinary'))

    def test_nonbinary_hyphenated(self):
        self.assertEqual('X', derive_gender_from_pronouns('Blah blah.  Non-binary'))


    def test_nogendermentioned(self):
        self.assertEqual(None, derive_gender_from_pronouns('Blah blah.'))
