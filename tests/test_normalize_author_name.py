#!/usr/bin/env python3

import unittest

from ..normalize_author_name import normalize_name


class TestNormalizeName(unittest.TestCase):

    def test_regular_name(self):
        self.assertIsNone(normalize_name('Alastair Reynolds'))

    def test_single_initial_good_format(self):
        self.assertIsNone(normalize_name('T. Kingfisher'))

    def test_single_initial_no_full_stop(self):
        self.assertEqual('T. Kingfisher', normalize_name('T Kingfisher'))

    def test_single_initial_no_space(self):
        self.assertEqual('T. Kingfisher', normalize_name('T.Kingfisher'))

    # Q: Should we try to make sense of silly input like "TKingfisher"?


    def test_double_initial_good_format(self):
        self.assertIsNone(normalize_name('N. K. Jemisin'))

    def test_double_initial_no_full_stops(self):
        self.assertEqual('N. K. Jemisin', normalize_name('NK Jemisin'))

    def test_double_initial_no_space(self):
        self.assertEqual('N. K. Jemisin', normalize_name('N.K. Jemisin'))

    def test_double_initial_mixed_errors(self):
        self.assertEqual('N. K. Jemisin', normalize_name('N. K Jemisin'))

    def test_double_initial_mixed_errors_reversed(self):
        self.assertEqual('N. K. Jemisin', normalize_name('N K. Jemisin'))

    # Can the next example be easily handled?  How would we disambiguate from
    # stuff like 'St. John Ervine" (author_id=164467) or
    # "Dr. Wernher von Braun" (author_id=170501) which should be left as-is?
    # Leaving on-hold for now
    #def test_double_initial_mixed_errors_another(self):
    #     self.assertEqual('N. K. Jemisin', normalize_name('NK. Jemisin'))


    # TODO: "Philip K Dick" -> "Philip K. Dick", 'James S.A. Corey" etc


