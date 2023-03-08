#!/usr/bin/env python3
"""
Note: These tests rely on the database, as some of the tested functions are
essentially SQL queries with a bit of tweaking in Python.
"""

from datetime import date
import unittest

from sqlalchemy.exc import OperationalError

from ..common import (get_connection, parse_args)
from ..title_publications import (get_publications_for_title_ids, get_earliest_pub)



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


class TestGetEarliestPub(unittest.TestCase):
    conn = get_connection()

    def test_simple_case(self):
        # Story (that as of 2023-03-08) has no variants
        ret = get_earliest_pub(self.conn, [995973])
        # any of 286985, 564951 or 306425, which are all pubs of Solaris Book of New SF 3,
        # title 995963.  (The first 2 IDs have 2009-02-00 dates, the last one has 2009-03-02,
        # so in theory shouldn't appear, but as it has a "real" date, it would be OK IMHO.)
        self.assertIn(ret['pub_id'], {286985, 564951, 306425})

    def test_simple_case_country_us(self):
        # Story (that as of 2023-03-08) has no variants
        ret = get_earliest_pub(self.conn, [995973], only_from_country='US')
        # There's only one $ pub
        self.assertEqual(ret['pub_id'], 286985)

    def test_simple_case_country_uk(self):
        # Story (that as of 2023-03-08) has no variants
        ret = get_earliest_pub(self.conn, [995973], only_from_country='GB')
        # There are 2 GBP pubs
        self.assertIn(ret['pub_id'], {564951, 306425})

    def test_parent_author_later_pub(self):
        # Paul (J.) McAuley's Elves of Antarctica, only appeared under that author name
        # in a Dozois Year's Best dated 2017-07-00.  (NB: wouldn't surprise me if that data is
        # incorrect and might one day get changed...)
        ret = get_earliest_pub(self.conn, [2029410])
        self.assertIn(ret['pub_id'], {619996, 625887})

    def test_variant_author_earlier_pub(self):
        # Paul McAuley's Elves of Antarctica, first appeared under that author name
        # in Strahan's Drowned Worlds (2016-07-00 or 2016-07-12)
        ret = get_earliest_pub(self.conn, [2029345])
        self.assertIn(ret['pub_id'], {573368, 573658, 768604})

    def test_use_both_title_ids(self):
        ret = get_earliest_pub(self.conn, [2029345, 2029410])
        self.assertIn(ret['pub_id'], {573368, 573658, 768604})
