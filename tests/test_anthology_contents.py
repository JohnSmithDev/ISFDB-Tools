#!/usr/bin/env python
"""
Note: These tests rely on the database, and as such are prone to breakage if
the data being tested changes.
"""

import datetime
from collections import namedtuple

import unittest


from ..common import (get_connection, parse_args)

from ..anthology_contents import (TitleStuff, PubStuff, get_contents_of_title,
                                  postprocess_contents)



RETIEF_EMISSARY_TO_THE_STARS = 30301



class TestPostProcessContents(unittest.TestCase):
    conn = get_connection()

    def test_pub_inconsistency(self):
        # As of 2021-03-28, Retief: Emissary to the Stars has 9 pubs, all of
        # which have contents, but they are inconsistent
        retief_raw_rows = list(get_contents_of_title(self.conn,
                                                     RETIEF_EMISSARY_TO_THE_STARS))
        ret = postprocess_contents(retief_raw_rows)
        distilled_ret = sorted((k.title, len(v)) for k, v in ret.items())
        self.assertEqual([
            ("An Excerpt from Retief & the Warlords", 4),
            ("Diplomat-in-Arms", 1),
            ("Giant Killer", 6),
            ("The All-Together Planet", 1),
            ("The Forest in the Sky",6),
            ("The Garbage Invasion",9),
            ("The Hoob Melon Crisis" ,9),
            ("The Negotiators",9),
            ("The Secret" ,1),
            ("The Troubleshooter" , 9),
            ("Trick or Treaty" , 6)], distilled_ret)

