#!/usr/bin/env python3
"""
Note: These tests rely on the database, as some of the tested functions are
essentially SQL queries with a bit of tweaking in Python.
"""

from datetime import date
import unittest

from sqlalchemy.exc import OperationalError

from ..common import (get_connection, parse_args)
from ..publication_history import get_publications


REVENGER_DETAILS = (2034339, 'Alastair Reynolds', 'Revenger', 0)
WAYDOWNDARK_CHILD_DETAILS = (1866037, 'J. P. Smythe', 'Way Down Dark', 1866038)
WAYDOWNDARK_PARENT_DETAILS = (1866038, 'James Smythe', 'Way Down Dark', 0)



class TestGetPublications(unittest.TestCase):
    conn = get_connection()

    def test_wdd(self):
        wdd_ids = [WAYDOWNDARK_CHILD_DETAILS[0], WAYDOWNDARK_PARENT_DETAILS[0]]
        ret = get_publications(self.conn, wdd_ids)
        # print(ret)
        # See http://www.isfdb.org/cgi-bin/title.cgi?1866037
        # and http://www.isfdb.org/cgi-bin/title.cgi?1866038
        self.assertEqual({'GB': [('tp', date(2015, 7, 2), '9781444796322'),
                                 ('tp', date(2016, 4, 7), '9781444796339')],
                          'US': [('hc', date(2016, 10, 4), '9781681443850'),
                                 ('ebook', date(2016, 10, 4), '9781681443836'),
                                 ('tp', date(2017, 10, 3), '9781681443843')]},
                         ret)

