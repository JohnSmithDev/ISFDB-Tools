#!/usr/bin/env python3
"""
Hacky attempt to cover the many variants on publisher names present in ISFDB.

This might be better done as JSON for interoperability, but I think this needs
comments to explain/document things, and I hate the "__comment__" hack you
sometimes see in JSON.  I've used double quotes " rather than apostrophes '
so that this could at least be converted to JSON easily (I think?).

The (current) argument handling logic aborts if a publisher isn't explicitly
defined here, which is why there are several one-to-one entries.
"""

PUBLISHER_VARIANTS = {
    # UK publishers
    "Gollancz": [
        # http://www.isfdb.org/cgi-bin/se.cgi?arg=gollancz&type=Publisher
        "BCA by arrangement with Gollancz",
        "Gollancz",
        "Gollancz / Orion",
        "Gollancz / Orion / SFBC",
        "Gollancz / SFBC",
        "Gollancz Readers Union",
        "Millennium / Gollancz",
        "Millennium / Victor Gollancz",
        "Mundanus Ltd. & Gollancz",
        "Puffin Books / Victor Gollancz",
        "VGSF",
        "VGSF / Gollancz",
        "VGSF / Victor Gollancz",
        "Victor Gollancz",
        "Victor Gollancz and the Cresset Press"
    ],

    # Del Rey? Penguin ?

    # Hodder ?

    # Jo Fletcher?

    "Orbit UK": [
        "Orbit",
        "Orbit / Little, Brown", # 2 pubs in 1999 and 2012
        "Orbit / Little, Brown UK", # 19 pubs between 1992 and 2011
        "Orbit / Time Warner Books UK", # 3 pubs in 2004 and 2005
        "Orbit Book / Futura Publications" # 9 pubs 1974-1977 and 1988-1989
        "Orbit / Futura",  # 191 pubs 1974-1990
        "Orbit / Futura Publications", # 7 pubs 1974-1988
        "Orbit/Future/General" # 1 pub 1984
    ],
    "Harper Voyager UK": [
        "Harper Voyager (UK",
        "HarperVoyager",
        "HarperVoyager / HarperCollinsPublishers"
    ],
    "Tor UK": [
        "Tor UK",
        "Pan Books",
        "Macmillan UK",
        "Pan / Macmillan", # (only 1 pub from 1981)
        "Pan Macmillan UK",  # (only 3 pubs betweeen 1992 and 2015)
        "Tor / Pan Macmillan UK" # 305 pubs between 1994 and 2016
        # Possibles....
        # "Picador / Pan Books"  (only 8 titles betwen 1971 and 2020)
        # "Piccolo / Pan Books" (only 8 pubs betwen 1972 and 1979)
        # "Piper / Pan Books" (one 1 pub in 1964)
        # "Palgrave Macmillan" - non-fiction (academic?) publisher

    ],

    ###
    ### US publishers
    ###

    "Ace": [
        "Ace / BOMC",
        "Ace Books",
        "Ace Books / Berkley",
        "Ace Books / SFBC",
        "Ace Science Fiction Books",
        "Ace Science Fiction Books / SFBC"
        # "Ace Star" ?
        # "Ace Star / Ace Books" ?
        ],

    "Baen": [
        "Baen",
        "Baen / SFBC",
        "Baen Books",
        "Baen Books / SFBC",
        "Baen Fantasy",
        "Baen Science Fiction Books",
        "Starline / Baen"
    ],


    "Bantam": [ # This is likely incomplete, there are 37 pubs with this in tehir name
        "Bantam Books",
        "Bantam Books / BCE",
        "Bantam Books / BOMC",
        "Bantam Books / QPBC",
        "Bantam Books / SFBC",
        # Ignoring UK and Australian "Bantam"s, including
        # Bantam Press,
        # Others to ignore are:
        # Bantam Publications

        # Unsure about:
        # Bantam Spectra (with variants)


    ],

    "DAW": [
        "DAW Books",
        "DAW Books / New American Library of Canada",  # 632 pubs 1972-1987
        "DAW Books / SFBC" # 186 pubs 1972-2016
    ],

    "Del Rey": [
        "Del Rey",
        "Del Rey / Ballantine",
        "Del Rey / Ballantine (Canada)",
        "Del Rey / Ballantine / BOMC",
        "Del Rey / Ballantine / QPBC",
        "Del Rey / Ballantine / SFBC",
        "Del Rey / SFBC",
        "Del Rey Impact / Ballantine",
        "LucasBooks / Del Rey / Ballantine",
        "LucasBooks / Del Rey / Ballantine / SFBC",
        "LucasBooks / Del Rey / SFBC"
    ],

    "Harper Voyager US": [
        "Harper Voyager",
        "Harper Voyager / SFBC"
    ],

    "Orbit US": [
        "Orbit (US)",
        "Orbit (US) / SFBC",
        "Orbit / SFBC" # 6 pubs betwen 2008 and 2016, all USD prices
    ],

    "Saga Press": {
        "Saga Press",
        "Saga Press / Gallery",
        "Saga Press / SFBC",
        "Saga Press / Simon & Schuster"
    },

    "Tor": [
        # This explicitly excludes Tor.com, Tor Teen and Tor UK, Fischer Tor, etc
        "Tor",
        "Tor / SFBC",
        # What is this?  It's not listed at https://en.wikipedia.org/wiki/Tor_Books#Imprints
        "Tor Fantasy"
    ],


    ###
    ### Global publishers
    ###

    "Amazon": ["47North", "Thomas & Mercer"],
    "Angry Robot": ["Angry Robot"],
    "Titan Books": [
        "Titan Books",
        "Titan Books / Design Studio Press",
        "Titan Books / SFBC",
        "Hard Case Crime / Titan Books"
        # Deliberately missing: Titan Comics; Titan Magazines
        # Unsure about: Titan Publishing
    ],
    "Tor.com": ["Tor.com"],
    "Solaris": [ # Would this be better/more accurate as Rebellion as the parent?
        "Solaris",
        "Abaddon Books",
        "Rebellion"
    ]
}
