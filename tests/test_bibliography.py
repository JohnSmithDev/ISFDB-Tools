#!/usr/bin/env python
"""
Note: These tests rely on the database, and as such are prone to breakage if
the data being tested changes.
"""

import datetime
from collections import namedtuple

import unittest

from sqlalchemy.exc import OperationalError

from ..common import (get_connection, parse_args)
from ..publication_history import (get_publications_by_country,
                                   PublicationDetails)

# TODO: there are other functions (probably more easily testable) in that module
from ..bibliography import (get_author_bibliography, PubStuff)


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

def make_title_id_to_details_map(books):
    """
    A more detailed alternative to extract_core_bits(), if you want to
    delve deeper
    """
    return {z.title_id: z for z in books}


class TestBibliography(unittest.TestCase):
    # There's a *lot* more should be tested...
    conn = get_connection()
    maxDiff = None


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
            # Unveiling Claudia is non-fiction, not sure if this is something
            # that was changed in the database after this test was written, or
            # if functionality was changed?  (The call to get_author_bibliography()
            # above explicitly states NOVEL
            # (102959, 'Unveiling Claudia: A True Story of Serial Murder', 1986), # non genre
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

    def test_get_bibliography_neal_asher_mindgames_1992(self):
        """
        "Mindgames: Fool's Mate" was first published in 1992 under the name
        "Neal L. Asher"
        http://www.isfdb.org/cgi-bin/title.cgi?864454 (parent title ID as Neal Asher)
        http://www.isfdb.org/cgi-bin/title.cgi?17670 (variant title ID as Neal L. Asher)
        At one point, this was only showing as a later 2009 pub by
        "Neal Asher", omitting the earlier "Neil L Asher" pub.

        There are - or rather were - similar issues with "Paul J. McAuley" and "Paul
        McAuley"; any pubs not belonging to the parent author ID were
        missing, and if all were assigned to the variant author ID - like
        all recent McAuley books I believe - then they were missing altogether.
        This is now fixed, albeit at the expense of 2 DB queries.
        """
        na_raw = get_author_bibliography(self.conn, 'Neal Asher',
                                         MAIN_TYPES_OF_INTEREST)
        na_dict = make_title_id_to_details_map(na_raw)
        # Because the Neil L Asher pub of Mindgames (17670) came out before the
        # parent title (864454)'s pub, the former ID will have been picked up
        # as the primary ID.  Not sure if this will be a problem, or at least
        # confusing...
        self.assertIn(17670, na_dict) # Sanity check
        mindgames = na_dict[17670]
        # And verify that both pubs are known:
        self.assertEqual([PubStuff(pub_id=22266,
                                   date=datetime.date(1992, 1, 1),
                                   format='tp',
                                   price='£1.99',
                                   publisher='Club 199'),
                          PubStuff(pub_id=671664,
                                   date=datetime.date(2018, 6, 6),
                                   format='tp',
                                   price='$7.99',
                                   publisher='Neal Asher')], mindgames.all_pub_stuff)

