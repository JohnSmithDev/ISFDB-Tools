#!/usr/bin/env python3
"""
Some manually curated expansion mappings of stuff that isn't modelled in the
database as I'd like it - comparable to the variant titles and authors, which
do model this sort of thing within the database.

Possible future areas where this might apply:

* Tags
* Others?
"""


from publisher_variants import PUBLISHER_VARIANTS


# keys should match the values in common.py for arguments
EXPANSION_MAPPINGS = {
    'publisher': PUBLISHER_VARIANTS
}
