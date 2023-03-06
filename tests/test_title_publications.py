#!/usr/bin/env python3
"""
Note: These tests rely on the database, as some of the tested functions are
essentially SQL queries with a bit of tweaking in Python.
"""

from datetime import date
import unittest

from sqlalchemy.exc import OperationalError

from ..common import (get_connection, parse_args)
from ..title_publications import (get_publications_for_title_ids,)



class TestGetPublicationsForTitleIds(unittest.TestCase):
    conn = get_connection()

    def test_title_with_just_one_id(self):
        ret = get_publications_for_title_ids(self.conn, [1898595]) # Roboteer by Alex Lamb
        pub_ids = set([z['pub_id'] for z in ret])
        self.assertEqual({533294, 568146, 611251}, pub_ids)

    def test_title_with_two_ids_first(self):
        ret = get_publications_for_title_ids(self.conn, [2996521]) # Nettle & Bone
        pub_ids = set([z['pub_id'] for z in ret])
        self.assertEqual({885254, 885255, 885256, 929230}, pub_ids)

    def test_title_with_two_ids_second(self):
        ret = get_publications_for_title_ids(self.conn, [3016273]) # Nettle and Bone
        pub_ids = set([z['pub_id'] for z in ret])
        self.assertEqual({892929, 895150}, pub_ids)

    def test_title_with_two_ids_both(self):
        ret = get_publications_for_title_ids(self.conn, [2996521, 3016273])
        pub_ids = set([z['pub_id'] for z in ret])
        self.assertEqual({885254, 885255, 885256, 892929, 895150, 929230}, pub_ids)

    def test_title_with_no_pubs(self):
        # The parent "Ursula Vernon" title record doesn't have any pubs itself
        ret = get_publications_for_title_ids(self.conn, [2996522])
        self.assertEqual([], ret)
