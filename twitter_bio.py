#!/usr/bin/env python3
"""
Library to download Twitter bios and parse them for any useful information -
currently just gender (from pronouns) if possible, but maybe location as well
in the future?

The official API seems to be as documented at:
https://developer.twitter.com/en/docs/accounts-and-users/follow-search-get-users/api-reference/get-users-show.html

but it seems you (now?) need to be a registered Twitter developer, and that
in turn seems to need you to tell Twitter what you want to use their API for,
so sod that...

Obv. this is highly breakable if/when they screw around with their HTML...

"""

import logging
import pdb
import re
import sys

from bs4 import BeautifulSoup

from downloads import (download_file_only_if_necessary, UnableToSaveError)

class UnableToDownloadOrExtractBio(Exception):
    pass


def get_twitter_bio(url):
    try:
        fn  = download_file_only_if_necessary(url)
    except UnableToSaveError as err:
        raise UnableToDownloadOrExtractBio('Failed to get %s' % (url))
    with open(fn) as inputstream:
        soup = BeautifulSoup(inputstream, 'lxml')

        bio_para_el = soup.find('p', {'class': 'ProfileHeaderCard-bio'})
        if bio_para_el:
            return re.sub('\s+', ' ', bio_para_el.text)
        # This could fail if the account has been suspended e.g.
        # https://twitter.com/NotRashKnee / Roshani Chokshi
    raise UnableToDownloadOrExtractBio('Failed to extract bio from %s' % (url))

def derive_gender_from_pronouns(text, reference=None):
    # This is super hacky and basic, I need to find more examples in the wild.
    # Plus maybe things are more complicated than pronoun => gender???
    lc_text = text.lower()
    if re.search('\Wshe[/]her\W', lc_text) or \
       re.search('\Wshe[/]her$', lc_text):
        return 'F'
    elif re.search('\Whe/him\W',  lc_text) or \
         re.search('\Whe/him$',  lc_text) or \
         re.search('[^s]he[,/]\s*his\W', lc_text) or \
         re.search('\(him\)', lc_text):
        return 'M'
    elif re.search('non\W?binary', lc_text):
        # TODO: neopronouns...
        return 'X'
    else:
        logging.warning('No pronouns found in %s (ref=%s)' % (text, reference))
        return None

def get_gender_from_twitter_bio(url):
    # TODO (maybe): have a 2-element tuple response similar to the Wikipedia
    # stuff, so that caller has some idea where we got the info from (or not)
    try:
        bio = get_twitter_bio(url)
    except UnableToDownloadOrExtractBio as err:
        return None
    return derive_gender_from_pronouns(bio, reference=url)


if __name__ == '__main__':
    bio = get_twitter_bio(sys.argv[1])
    gender = derive_gender_from_pronouns(bio)
    print('%s : %s' % (gender, bio))


