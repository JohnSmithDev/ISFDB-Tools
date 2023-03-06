#!/usr/bin/env python3
"""
Note: These tests rely on the database, as some of the tested functions are
essentially SQL queries with a bit of tweaking in Python.
"""

from datetime import date
import unittest

# from sqlalchemy.exc import OperationalError

from ..common import (get_connection, parse_args)
from ..title_contents import (get_pub_contents, NoContentsFoundError)


REVENGER_DETAILS = (2034339, 'Alastair Reynolds', 'Revenger', 0)
WAYDOWNDARK_CHILD_DETAILS = (1866037, 'J. P. Smythe', 'Way Down Dark', 1866038)
WAYDOWNDARK_PARENT_DETAILS = (1866038, 'James Smythe', 'Way Down Dark', 0)



class TestGetPublications(unittest.TestCase):
    conn = get_connection()

    def test_exception_when_no_contents(self):
        # !!! THIS TEST WILL BREAK WHEN THE CONTENTS ARE ENTERED INTO THE DB !!!
        # Best American SF & F 2022, has 2 pubs as of 2023-03-06
        # https://www.isfdb.org/cgi-bin/title.cgi?3086477

        with self.assertRaises(NoContentsFoundError):
            whatever = get_pub_contents(self.conn, (916967, 918280))
