#!/usr/bin/env python3
"""
Use Wikipedia categories if possible to determine an author's gender.
"""


from collections import Counter
import logging
import pdb
import re
import sys

from sqlalchemy.sql import text

from common import (get_connection, parse_args, AmbiguousArgumentsError)
from author_aliases import get_author_alias_ids, get_author_aliases
from award_related import extract_authors_from_author_field

from twitter_bio import get_gender_from_twitter_bio
from human_names import derive_gender_from_name
from wikipedia_related import (get_author_gender_from_wikipedia_pages,
                               is_wikipedia_url)

class UnableToDeriveGenderError(Exception):
    pass


def get_urls(conn, author_ids, include_priority_values=False):
    """
    Return a list of URLs relevant to the supplied author IDs.  The returned
    list is sorted so that the earlier the relevant ID was in author_ids,
    the earlier (i.e. more prioritized) it'll be in the returned list.
    Secondarily we also prioritize shorter URLs over longer ones - this is to
    favour Wikipedia pages like John_Doe over Bibliography_of_John_Doe
    """
    # I'm not sure where ISFDB gets the "display label" for links from, I'm
    # guessing it's maybe hardcoded as some links don't have it e.g. a couple
    # for http://www.isfdb.org/cgi-bin/ea.cgi?20
    query = text("""SELECT author_id, url
    FROM webpages wp
    WHERE wp.author_id IN :author_ids;""")
    rows = conn.execute(query, {'author_ids':author_ids})

    # print(author_ids)
    aid_priority = {}
    for i, aid in enumerate(author_ids):
        aid_priority[aid] = i
    priority_and_urls = []
    for r in rows:
        priority_and_urls.append(((aid_priority[r.author_id], len(r.url)),
                                  r.url))
    sorted_by_author_priority = sorted(priority_and_urls)
    # print(sorted_by_author_priority)
    if include_priority_values:
        return sorted_by_author_priority
    else:
        return [z[1] for z in sorted_by_author_priority]


# TODO: this should probably be in twitter_bio,py
def get_twitter_urls(urls):
    return [z for z in urls if 'twitter.com' in z]




def get_author_gender_from_ids(conn, author_ids, reference=None):
    """
    Returns 'M', 'F', 'X' (for other/nonbinary), 'H' (house pseudonym) or None
    (if unknown).
    reference is used solely for logging something more meaningful than
    ID numbers if no gender found.  (TODO: This isn't strictly true, as the
    human-names stuff will use this, but that should be refactored I think)
    """
    prioritized_urls = get_urls(conn, author_ids)
    wikipedia_urls = [z for z in prioritized_urls if is_wikipedia_url(z)]

    gender, category = get_author_gender_from_wikipedia_pages(wikipedia_urls,
                                                              reference=reference)

    if gender:
        return gender, 'wikipedia:%s' % (category)

    twitter_urls = get_twitter_urls(prioritized_urls)
    if not twitter_urls:
        logging.warning('No Twitter link(s) for %s' % (reference))
    for twitter_url in twitter_urls:
        gender = get_gender_from_twitter_bio(twitter_url)
        if gender:
            return gender, 'twitter:Bio at %s' % (twitter_url)

    # TODO: factor this next bit out and/or look up the names if they weren't
    # passed through
    try:
        return get_gender_from_names(conn, reference)
    except UnableToDeriveGenderError:
        return None, category or None


def gender_response_from_name(name, original_name):
    gender = derive_gender_from_name(name.split(' ')[0])
    if gender:
        if original_name and name != original_name:
            return gender, 'human-names:%s' % (name)
        else:
            return gender, 'human-names'
    else:
        return None, None

def get_gender_from_names(conn, author_names, look_up_all_names=True):
    # TODO: lots to make this less sucky:
    # * Use the proper columns in ISFDB for given/first name (I think there is
    #   one?)
    # * Try to use non-first names e.g. "A. Bertram Chandler" (hopefully less
    #   of an issue now that we are also checking the variant names)
    # * conn would be better as an optional arg, but we have a well established
    #   pattern of it being the first arg, so...
    for initial_name in author_names:
        if conn and look_up_all_names:
            all_names = get_author_aliases(conn, initial_name)
        else:
            all_names = author_names
        for name in all_names:
            gender, detail = gender_response_from_name(name, author_names[0])
            if gender:
                return gender, detail
        else:
            raise UnableToDeriveGenderError('Unable to derive gender for "%s" (inc variants)' %
                                            (author_names))

def get_author_gender(conn, author_names):
    """
    Returns a tuple of (gender-char, source)
    gender-char is one of 'M', 'F', 'X' (for other/nonbinary) or None (if unknown).
    source is a string of format 'source' or 'source:detail', e.g.
    'human-names', 'wikipedia:English male novelists', 'twitter:bio'.

    """
    author_ids = []
    for name in author_names:
        # Q: Would having multiple names muck up any logic dependent on the
        #    ordering of the IDs that get_author_aliases_ids() returns?
        author_ids.extend(get_author_alias_ids(conn, name))
    if author_ids:
        return get_author_gender_from_ids(conn, author_ids, reference=author_names)
    else:
        # raise AmbiguousArgumentsError('Do not know author "%s"' % (author_names))
        logging.warning('Author "%s" does not have a proper ISFDB entry' % (author_names))

        try:
            return get_gender_from_names(None, author_names, look_up_all_names=False)
        except UnableToDeriveGenderError:
            return None, 'No author entry in ISFDB, and could not derive gender from name'



if __name__ == '__main__':
    # logging.getLogger().setLevel(logging.DEBUG)
    args = parse_args(sys.argv[1:],
                      description="Return an author's gender (if known)",
                      supported_args='av')

    conn = get_connection()
    gender, source = get_author_gender(conn, args.exact_author)
    print('%s (source: %s)' % (gender, source))
