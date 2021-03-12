#!/usr/bin/env python
"""
Note: These tests rely on the database,
"""

# from datetime import date
from collections import namedtuple
import unittest

from sqlalchemy.exc import OperationalError

from ..common import (get_connection, parse_args)
from ..publication_history import (get_publications_by_country,
                                   PublicationDetails)

# TODO: there are other functions (probably more easily testable) in that module
from ..bibliography import (get_author_bibliography)


CoreBookInfo = namedtuple('CoreBookInfo', 'id, title, year')

MAIN_TYPES_OF_INTEREST = ['NOVEL', 'CHAPBOOK', 'COLLECTION', 'OMNIBUS']

def extract_core_bits(books):
    """
    Simplify a list of book objects into something we can easily test.

    You don't want this if you're testing that the publication handling etc is
    correct, but this is useful for simple checks that the right titles are
    included and the wrong ones excluded
    """
    return [CoreBookInfo(z.title_id, z.title, z.year) for z in books]

class TestBibliography(unittest.TestCase):
    # There's a *lot* more should be tested...
    conn = get_connection()

    def test_get_bibliography_novels_simple(self):
        # Keyes only wrote novels (the Flowers... novella seems to have never
        # been published in its own right as a CHAPBOOK)
        ret = get_author_bibliography(self.conn, 'Daniel Keyes', ['NOVEL'])
        core_bits = extract_core_bits(ret)
        self.assertEqual([
            (1927, 'Flowers for Algernon', 1966),
            (12314, 'The Touch', 1968),
            (12315, 'The Fifth Sally', 1980),
            (102957, 'The Minds of Billy Milligan', 1981), # non genre
            (102959, 'Unveiling Claudia: A True Story of Serial Murder', 1986), # non genre
            (1232927, 'The Asylum Prophecies', 2009)], core_bits)
        # There's also a novel which was only published in Japanese translation:
        # http://www.isfdb.org/cgi-bin/title.cgi?1973995
        # Non-English titles/variants are currently excluded

    def test_get_bibliography_real_name_and_aliases_match(self):
        sm_raw = get_author_bibliography(self.conn, 'Seanan McGuire',
                                         MAIN_TYPES_OF_INTEREST)
        sm_core  = extract_core_bits(sm_raw)
        mg_raw = get_author_bibliography(self.conn, 'Mira Grant',
                                         MAIN_TYPES_OF_INTEREST)
        mg_core  = extract_core_bits(mg_raw)
        self.assertEqual(sm_core, mg_core)
        adb_raw = get_author_bibliography(self.conn, 'A. Deborah Baker',
                                         MAIN_TYPES_OF_INTEREST)
        adb_core  = extract_core_bits(adb_raw)
        self.assertEqual(sm_core, adb_core)

    def test_get_bibliography_ray_bradbury_excludes_gestalts_by_others(self):
        # This tests a bug that's been resolved by only looking for titles by
        # the canonical author, and not any of the aliases
        rb_raw = get_author_bibliography(self.conn, 'Ray Bradbury', # author_id=194
                                         MAIN_TYPES_OF_INTEREST)
        rb_core  = extract_core_bits(rb_raw)
        # Danger Planet is by "Brett Sterling", and alias used by 3 authors inc.
        # Bradbury, but in this case the real author is Edmond Hamilton
        # http://www.isfdb.org/cgi-bin/title.cgi?935565
        self.assertFalse((935565, 'Danger Planet', 1968) in rb_core)
