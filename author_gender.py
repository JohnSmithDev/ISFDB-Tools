#!/usr/bin/env python3
"""
Use Wikipedia categories if possible to determine an author's gender.
"""


from collections import Counter, namedtuple
import logging
import pdb
import re
import sys

from sqlalchemy.sql import text

from common import (get_connection, parse_args, AmbiguousArgumentsError)
from author_aliases import (get_author_alias_ids, get_author_aliases,
                            get_real_author_id)
from award_related import extract_authors_from_author_field

from twitter_bio import get_gender_from_twitter_bio
from human_names import derive_gender_from_name
from wikipedia_related import (get_author_gender_from_wikipedia_pages,
                               is_wikipedia_url)

class UnableToDeriveGenderError(Exception):
    pass

GenderAndSource = namedtuple('GenderAndSource', 'gender, source')

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
    Returns a GenderAndSource namedtuple for the provided author_ids.

    * author_ids is a list of one or more author_ids - however it is presumed
      that these are all aliases/pseudonyms to a single person - e.g. if we
      did 'select distinct author_id from pseudonyms where pseudonym in author_ids;'
      we would expect to get a single value back.  (Perhaps that might not be
      the case for joint-pseudonyms?)

      ** It should not be used for cases of multiple individuals collaborating
      on a novel, for example. **

      As a convenience, if there's just a single ID, you can pass it directly
      as an int, rather than having to wrap it in parentheses to turn it into a list.

    * reference is used solely for logging something more meaningful than
      ID numbers if no gender found.  Use get_author_gender_from_ids_and_then_name()
      if you need the name as a fallback.
    """

    if isinstance(author_ids, int):
        author_ids = [author_ids]

    prioritized_urls = get_urls(conn, author_ids)
    wikipedia_urls = [z for z in prioritized_urls if is_wikipedia_url(z)]

    gender, category = get_author_gender_from_wikipedia_pages(wikipedia_urls,
                                                              reference=reference)

    if gender:
        return GenderAndSource(gender, 'wikipedia:%s' % (category))

    twitter_urls = get_twitter_urls(prioritized_urls)
    if not twitter_urls:
        logging.warning('No Twitter link(s) for %s' % (reference))
    for twitter_url in twitter_urls:
        gender = get_gender_from_twitter_bio(twitter_url)
        if gender:
            return GenderAndSource(gender, 'twitter:Bio at %s' % (twitter_url))

    raise UnableToDeriveGenderError('Not able to get gender using author_ids %s (ref=%s)' %
                                    (author_ids, reference))



def get_author_gender_from_ids_and_then_name(conn, author_ids, name):
    try:
        return get_author_gender_from_ids(conn, author_ids, reference=name)
    except UnableToDeriveGenderError:
        return gender_response_from_name(name, name)

gagfiatn_cache = {}
def get_author_gender_from_ids_and_then_name_cached(conn, author_ids, name):
    raw_key_bits = []
    for thing in (author_ids, name):
        if isinstance(thing, (list, tuple, set)):
            raw_key_bits.extend(thing)
        else:
            raw_key_bits.append(thing)
    cache_key = tuple(raw_key_bits)
    try:
        return gagfiatn_cache[cache_key]
    except KeyError:
        x = get_author_gender_from_ids_and_then_name(conn, author_ids, name)
        gagfiatn_cache[cache_key] = x
        return x


def gender_response_from_name(name, original_name):
    gender = derive_gender_from_name(name.split(' ')[0])
    if gender:
        if original_name and name != original_name:
            return GenderAndSource(gender, 'human-names:%s' % (name))
        else:
            return GenderAndSource(gender, 'human-names')
    else:
        return GenderAndSource(None, None)

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
            g_s = gender_response_from_name(name, author_names[0])
            if g_s.gender:
                return g_s
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
    # Not sure if this is happening - I would prefer to explicitly make it
    # only use 1 name if possible
    if len(author_names) != 1:
        logging.warning('get_author_gender: Multiple names passed: %s' % (author_names))


    author_ids = []
    for name in author_names:
        # Q: Would having multiple names muck up any logic dependent on the
        #    ordering of the IDs that get_author_aliases_ids() returns?
        author_ids.extend(get_author_alias_ids(conn, name))
    try:
        if not author_ids:
            raise UnableToDeriveGenderError('Author "%s" does not have a proper ISFDB entry' %
                                            (author_names))
        return get_author_gender_from_ids(conn, author_ids, reference=author_names)
    except UnableToDeriveGenderError as err:
        # raise AmbiguousArgumentsError('Do not know author "%s"' % (author_names))
        logging.warning('%s - will try to get gender from name instead' % (err))
        all_author_names = author_names[:] # copy
        for author_id in author_ids:
            all_author_names.extend(get_author_aliases(conn, author_id))

        try:
            return get_gender_from_names(None, all_author_names, look_up_all_names=False)
        except UnableToDeriveGenderError:
            return GenderAndSource(None,
                                   'No ISFDB author entry, and could not derive gender from name')


gag_cache = {}

def get_author_gender_cached(conn, author_names):
    cache_key = tuple(author_names)
    try:
        return gag_cache[cache_key]
    except KeyError:
        x = get_author_gender(conn, author_names)
        gag_cache[cache_key] = x
        return x


if __name__ == '__main__':
    # logging.getLogger().setLevel(logging.DEBUG)
    args = parse_args(sys.argv[1:],
                      description="Return an author's gender (if known)",
                      supported_args='av')

    conn = get_connection()
    gender, source = get_author_gender(conn, args.exact_author)
    print('%s (source: %s)' % (gender, source))
