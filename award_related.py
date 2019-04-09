#!/usr/bin/env python3
"""
Functions relevant to how ISFDB handles awards, but which don't have any
direct connection to the databse.
"""



BOGUS_AUTHOR_NAMES = ('', '********')

DODGY_TITLES_AND_PSEUDO_AUTHORS = {
    'No Award': 'Noah Ward'
}

# This is a nasty hack for pseudonyms, TODO: think how to do it better
DONT_USE_THESE_REAL_NAMES = (
    'Compton Crook',
)

MULTIPLE_AUTHORS_SEPARATOR = '+' # e.g. Brandon Sanderson + someone I think?
PSEUDONYM_SEPARATOR = '^' # e.g. Edmond Hamilton^Brett Sterling (Retro Hugo Novel 1946)


def extract_authors_from_author_field(raw_txt):
    """
    AFAIK the use of MULTIPLE_AUTHORS_SEPARATOR and PSEUDONUM_SEPARATOR is
    unique to the awards table - if not, then this function would probably
    be best moved elsewhere.
    """

    txt = raw_txt.strip()
    if txt.startswith('(') and txt.endswith(')'): # "(Henry Kuttner+C. L. Moore)" - but see below
        txt = txt[1:-1].strip()
    if PSEUDONYM_SEPARATOR in txt:
        # We only want to use one of these
        real_name, pseudonym = txt.split(PSEUDONYM_SEPARATOR)
        # For now assume the real name is right TODO: test both, and use the best
        # UPDATE: That assumption turned out to be wrong for "Compton Crook^Stephen Tall"

        # Note that we can have both separators e.g.
        # '(Henry Kuttner+C. L. Moore)^Lewis Padgett' hence the recursion
        if real_name in DONT_USE_THESE_REAL_NAMES:
            return extract_authors_from_author_field(pseudonym)
        else:
            return extract_authors_from_author_field(real_name)
    else:
        authors = txt.split(MULTIPLE_AUTHORS_SEPARATOR)
    return [z.strip() for z in authors] # extra strip just to be super-sure

def replace_author_name_if_necessary(title, author):
    if title in DODGY_TITLES_AND_PSEUDO_AUTHORS and author in BOGUS_AUTHOR_NAMES:
        return DODGY_TITLES_AND_PSEUDO_AUTHORS[title]
    else:
        return author

def sanitise_authors_for_dodgy_titles(title, authors):
    """
    If the title is known to be dubious, replace any authors that are similar
    dodgy.  (This is basically to sanitise No Award entries.)
    """
    if title in DODGY_TITLES_AND_PSEUDO_AUTHORS:
        replacement = DODGY_TITLES_AND_PSEUDO_AUTHORS[title]
        authors = [replace_author_name_if_necessary(title, z) for z in authors]
    return authors
