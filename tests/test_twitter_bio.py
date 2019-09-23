#!/usr/bin/env python3

import unittest

from ..twitter_bio import derive_gender_from_pronouns

class TestDeriveGenderFromPronouns(unittest.TestCase):

    ### First, some simple, unambiguous cases

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

    def test_genderqueer_oneword(self):
        self.assertEqual('X', derive_gender_from_pronouns('Blah blah.  Genderqueer'))

    def test_genderqueer_theyslashthem(self):
        self.assertEqual('X', derive_gender_from_pronouns('Blah blah.  They/them'))


    def test_nogendermentioned(self):
        self.assertEqual(None, derive_gender_from_pronouns('Blah blah.'))

    ### Now for some ambiguous/contradictory ones.  It's not clear to me what
    ### the optimal way to handle these is - I suspect there isn't one - but
    ### at least we should recognize these as ones we can't handle.
    ### TODO: the code being tested should throw a ContradictoryGendersDetectedError
    ### so that we know not to continue on checking other sources

    def test_contradictory_he_they(self):
        self.assertEqual(None, derive_gender_from_pronouns('Blah blah.  He/they'))

    def test_contradictory_she_her_they_them(self):
        self.assertEqual(None, derive_gender_from_pronouns('Blah blah.  She/her or they/them'))

    def test_contradictory_binary_and_nonbinary(self):
        # I've not encountered this in the wild for Twitter, but there is a
        # similar example on Wikipedia
        self.assertEqual(None, derive_gender_from_pronouns('Blah blah.  He/him.  Non-binary'))


    ### And finally, avoid false positives
    def test_false_positive_he_him(self):
        self.assertEqual(None, derive_gender_from_pronouns('I like the Himalaya mountains'))

    def test_false_positive_she_her(self):
        self.assertEqual(None, derive_gender_from_pronouns('Galoshe-herald.'))



    # TODO (not yet implemented in the underlying code):
    # * neopronouns
    # * pronoun.is links



