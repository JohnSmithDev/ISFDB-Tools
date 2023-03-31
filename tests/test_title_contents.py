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





class TestGetPublications(unittest.TestCase):
    conn = get_connection()

    def test_exception_when_no_contents(self):
        # !!! THIS TEST WILL BREAK IF/WHEN THE CONTENTS ARE ENTERED INTO THE DB !!!
        # Death on the Pitch: Extra Time
        # https://www.isfdb.org/cgi-bin/title.cgi?2797319
        # 2020 Blood Bowl anthology with no contents as of March 2023, so may be safe for a while?

        with self.assertRaises(NoContentsFoundError):
            whatever = get_pub_contents(self.conn, (806864,))
