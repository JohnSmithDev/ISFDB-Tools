#!/usr/bin/env python3
"""
Note: These tests rely on the database, as some of the tested functions are
essentially SQL queries with a bit of tweaking in Python.
"""

from datetime import date
import unittest

from sqlalchemy.exc import OperationalError

from ..common import (get_connection, parse_args)
from ..magazine_reviews import (_get_reviews, RepeatReviewBehaviour,
                                ReviewedWork)

class TestGetReviews(unittest.TestCase):
    conn = get_connection()

    def test_get_reviews(self):
        # This is a very basic exercising of the code, doesn't test anything difficult
        ret = _get_reviews(self.conn, 'Interzone', 'YEAR(pub_year) = :year',
                           {'year': 2010, 'countries': None, 'limit': None},
                            RepeatReviewBehaviour.DIFFERENT_MONTHS_ONLY)
        self.assertEqual(42, len(ret))
        self.assertEqual(['Black and White', 'Brain Thief', 'The Battle of the Sun',
                          "The Cardinal's Blades", 'The Sad Tale of the Brothers Grossbart'],
                         [z.title for z in ret[:5]])
