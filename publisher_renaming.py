#!/usr/bin/env python3
"""
Mappings for publisher names as they might appear on Amazon, Goodreads,
Waterstones etc, to the forms that they (probably) are on ISFDB.

This might be better moved into the isfdb_tools repo?
"""

# Keep these in alphabetic(ish) order
# TODO: restructure sp that regional values can be picked up programmatically
PUBLISHER_RENAMING = {
    'Angry Robot Books': 'Angry Robot',

    'Penguin': 'Penguin Books', # UK only

    'REBCA': '*Rebellion imprint* - either "Solaris" or "Abaddon Books"',
    'REBCA; Paperback Original edition':
    '*Rebellion imprint* - either "Solaris" or "Abaddon Books"',

    'Orion Publishing Group': 'Orion imprint - *PROBABLY* Gollancz'
}
