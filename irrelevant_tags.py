#!/usr/bin/env python3
"""
A list of tags/shelves/breadcrumbs/genres/sub-genres that are not relevant to
ISFDB.

NB: This will possibly not be used by any code elsewhere in this repo, but by
other projects that live elsewhere.  However, as it's very much tied to ISFDB,
it seems that this is a reasonable place for it to live.

TODO (maybe): Make this JSON for wider compatibility?  (So use " rather than ')

!!! Keep this all lower case and in alphabetic-ish order !!!
"""

ISFDB_IRRELEVANT_TAGS = {
    "advertising & society",

    "atlases"

    "biography: sport",
    "biography & autobiography / entertainment & performing arts",
    "biography & autobiography / science & technology",
    "biography & autobiography / general",

    "business strategy", "business & management", "business",
    "business/economics", "economic history", "economics: professional & general",

    "car racing", "automobile racing", "motor sports", "formula 1 & grand prix",

    "conjuring & magic",

    "crime & mystery", "crime & mystery fiction", "crime",

    "earth sciences", "geography", "environment", "law / land use",
    "environment",
    "natural history", "natural history: plants",
    "nature / plants / flowers", "nature / plants / trees",


    "entertainment & performing arts", "other performing arts",

    "great britain/british isles",

    "history", "historical events & topics", "general & world history",
    "history / europe / general", "historical periods",
    "postwar 20th century history: 1945 to 2000", "history / world",



    "information technology industries", "social networking", "social network",
    "internet advertising", "e-commerce", "internet - general",

    "international human rights law", "law / general", "legal history"

    "management",

    "military intelligence", "military - aviation",
    "wars & conflicts (other)",

    "music / individual composer & musician",

    "poetry, drama & criticism",

    "politics/intl relations", "political leaders & leadership",
    "political science", "government & constitution",
    "political science/comparative politics", "political science / general",
    "politics & government", "political corruption",
    'international relations',

    "great britain/politics and government",
    "american government", "government & constitution",

    "press & journalism", "media studies", "anf: media studies",
    "social science / media studies",

    "psychology", "sociology", "philosophy", "social psychology",
    "psychological testing & measurement", "popular psychology",
    "group or collective psychology", "sociology - general",

    "privacy & data protection",

    "religion / religion", "religion: comparative",

    "contemporary romance",

    "popular science", "science: general issues", "mathematics & science",
    "popular mathematics", "probability & statistics",
    "anf: popular science and mathematics",
    "testing & measurement", "science / history", "science / ethics",

    "social activists",

    "society & culture", "cultural studies",
    "social science / anthropology / cultural & social",


    "spiritualism", "self-help",

    "thriller & adventure",

    "anf: transport", "transport industries"
    }

