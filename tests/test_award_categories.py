#!/usr/bin/env python3

import unittest

from ..award_categories import render_year_ranges, convert_list_string_to_unique_years

class TestRenderYearRanges(unittest.TestCase):

    def test_empty(self):
        self.assertEqual('', render_year_ranges(''))

    def test_single_year(self):
        self.assertEqual('2001', render_year_ranges([2001]))

    def test_single_yyyymmdd(self):
        processed = convert_list_string_to_unique_years('2001-00-00')
        self.assertEqual('2001', render_year_ranges(processed))

    def test_contiguous_years(self):
        self.assertEqual('2001-2004', render_year_ranges([2001,2002,2003,2004]))

    def test_contiguous_yyyymmdds(self):
        processed = convert_list_string_to_unique_years('2001-00-00,2002-00-00,2003-00-00,2004-00-00')
        self.assertEqual('2001-2004',
                         render_year_ranges(processed))

    def test_separate_years(self):
        self.assertEqual('2001, 2004, 2010', render_year_ranges([2001,2004,2010]))

    def test_contiguous_yyyymmdds(self):
        processed = convert_list_string_to_unique_years('2001-00-00,2004-00-00,2010-00-00')
        self.assertEqual('2001, 2004, 2010',
                         render_year_ranges(processed))

    def test_mixed_years(self):
        self.assertEqual('2001-2004, 2010, 2012-2015',
                         render_year_ranges([2001,2002,2003,2004,2010,2012,2013,2014,2015]))

    def test_contiguous_yyyymmdds(self):
        processed = convert_list_string_to_unique_years('2001-00-00,2002-00-00,2003-00-00,2004-00-00,'
                                            '2010-00-00,'
                                            '2012-00-00,2013-00-00,2014-00-00,2015-00-00')
        self.assertEqual('2001-2004, 2010, 2012-2015',
                         render_year_ranges(processed))

    def test_mixed_years_character_overrides(self):
        self.assertEqual('2001 to 2004; 2010; 2012 to 2015',
                         render_year_ranges([2001,2002,2003,2004,2010,2012,2013,2014,2015],
                                            range_link=' to ', range_separator='; '))
