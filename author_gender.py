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
from bs4 import BeautifulSoup

from common import (get_connection, parse_args, AmbiguousArgumentsError)
from author_aliases import get_author_alias_ids
from downloads import (download_file_only_if_necessary, UnableToSaveError)
from award_related import extract_authors_from_author_field
from twitter_bio import get_gender_from_twitter_bio
from human_names import derive_gender_from_name

def get_urls(conn, author_ids, include_priority_values=False):
    """
    Return a list of URLs relevant to the supplied author IDs.  The returned
    list is sorted so that the earlier the relevant ID was in author_ids,
    the earlier (i.e. more prioritized) it'll be in the returned list.
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
        priority_and_urls.append((aid_priority[r.author_id], r.url))
    sorted_by_author_priority = sorted(priority_and_urls)
    # print(sorted_by_author_priority)
    if include_priority_values:
        return sorted_by_author_priority
    else:
        return [z[1] for z in sorted_by_author_priority]

def is_wikipedia_url(url, lang='en'):
    if lang:
        domain = '%s.wikipedia.org' % (lang)
    else:
        domain = 'wikipedia.org'
    return domain in url

def get_wikipedia_urls(urls):
    wiki_urls = [z for z in urls if is_wikipedia_url(z)]
    # Sort by length so that we prefer 'http://en.wikipedia.org/wiki/Andre_Norton'
    # over'http://en.wikipedia.org/wiki/Andre_Norton_bibliography'.  This may
    # need further tuning if/when we come across more entries with multiple
    # Wikipedia URLs.  (This might also be good for supporting non en wikis too?)
    return sorted(wiki_urls, key=len)

def get_twitter_urls(urls):
    return [z for z in urls if 'twitter.com' in z]


def DEPRECATED_get_wikipedia_url(urls): # Not sure that this was ever used?
    wiki_urls = get_wikipedia_urls(urls)
    if not wiki_urls:
        return None
    if len(wiki_urls) > 1:
        logging.warning('Multiple Wikipedia URLs, using first one: %s' % (wiki_urls))
    return wiki_urls[0]

def get_wikipedia_content(url):
    # TODO: this assumes the URL doesn't have parameters already - use urllib
    # to construct it more robustly.
    # Q: is the source Markdown better than downloading the HTML and using
    # Beautiful soup anyway?
    # md_url = url + '?action=raw'
    fn = download_file_only_if_necessary(url)
    return fn

def extract_categories_from_content(html_file):
    with open(html_file) as inputstream:
        soup = BeautifulSoup(inputstream, 'lxml')

        # There is some inline JavaScript that defines an object containing
        # a "wgCategories" property, but I don't think that'd be particularly
        # easy to extract compared to pulling out the links in #catlinks
        catlinks = soup.select_one('#catlinks')
        link_els = catlinks.findAll('a')
        # Ignore <a href="/wiki/Help:Category" title="Help:Category"> and anything similar
        category_els = [z for z in link_els if z['href'].startswith('/wiki/Category:')]
        categories = [z.text.strip().lower() for z in category_els]
        return categories

def remove_irrelevant_categories(categories):
    """
    Remove any categories which are (presumably) for Wikipedia internal/admin
    use.  Removing them is not strictly necessary, but makes things more
    readable when debugging.
    """

    def is_ignorable(cat):
        return re.search('wikipedia.articles.with.*identifiers$', cat, re.IGNORECASE) or \
            re.search('use.*from.*\d\d\d\d$', cat, re.IGNORECASE)

    return [z for z in categories if not is_ignorable(z)]

def determine_gender_from_categories(categories, reference=None):
    """
    Return a tuple of (gender-character, wiki-category-used)
    gender-character can be None, if which case wiki-category-used will be a list
    of all the categories.
     wiki-category-used is mainly returned for debugging purposes, I can't
    think of a reason it would be useful in normal circumstances
    """
    for cat in categories:
        if re.search(' male (novelist|writer|essayist|screenwriter|journalist|composer|singer|painter)s?$',
                     cat, re.IGNORECASE):
            return 'M', cat
        elif re.search(' male (short story |non.fiction |speculative.fiction )(writer|editor)s?$',
                     cat, re.IGNORECASE):
            return 'M', cat
        elif re.search('^male (\w+ )?(feminist|novelist|writer|essayist|blogger|painter)s?',
                     cat, re.IGNORECASE):
            return 'M', cat
        elif re.search('^male (speculative fiction )?(editor|novelist|writer)s?',
                     cat, re.IGNORECASE):
            return 'M', cat
        elif re.search('(female|women) (short story |comics |mystery )?(novelist|writer|editor|artist)s?$',
                       cat, re.IGNORECASE):
            return 'F', cat
        elif re.search('(female|women) (science fiction and fantasy |speculative fiction.)(editor|novelist|writer)s?$',
                       cat, re.IGNORECASE):
            return 'F', cat
        elif re.search(' (lesbian) (novelist|writer)s?$', cat, re.IGNORECASE):
            return 'F', cat
        elif re.search('(actresses)$', cat, re.IGNORECASE):
            return 'F', cat
        elif re.search('transgender and transsexual men$', cat, re.IGNORECASE):
            return 'M', cat
        elif re.search('transgender and transsexual women$', cat, re.IGNORECASE):
            return 'F', cat
        elif re.search('non.binary (writer|novelist)s?s', cat, re.IGNORECASE):
            return 'X', cat
        # Uncomment the next bit when we avoid false positive matches on it
        # e.g. Bruce Holland Rogers
        #elif cat in ('stratemeyer syndicate pseudonyms',):
        #    return 'H', cat

    logging.warning('Unable to determine gender for %s based on these categories: %s' %
                    (reference, categories))
    return None, categories

def get_author_gender_from_wikipedia_pages(urls, reference=None):
    """
    reference is only used for logging purposes - it could be any useful
    reference for debugging
    """
    # wiki_urls = get_wikipedia_urls(urls) # No - retain the supplied ordering
    wiki_urls = urls

    all_cats = set()
    for wiki_url in wiki_urls:
        if not is_wikipedia_url(wiki_url):
            logging.warning('Ignoring non-Wikipedia URL %s' % (wiki_url))
            continue
        try:
            wiki_file = get_wikipedia_content(wiki_url)
        except UnableToSaveError as err:
            logging.warning('Unable to get Wikipedia page %s' % (err))
            continue
        raw_categories = extract_categories_from_content(wiki_file)
        categories = remove_irrelevant_categories(raw_categories)
        all_cats.update(categories)
        gender, category = determine_gender_from_categories(categories, wiki_url)
        if gender:
            return gender, category
    else:
        if wiki_urls:
            logging.warning('No gender information found in %s' % (wiki_urls))
        else:
            logging.debug('No Wikipedia link for %s' % (reference))
        return None, all_cats


def get_author_gender_from_ids(conn, author_ids, author_names=None):
    """
    Returns 'M', 'F', 'X' (for other/nonbinary), 'H' (house pseudonym) or None
    (if unknown).
    author_names here is used solely for logging something more meaningful than
    ID numbers if no gender found.
    """
    prioritized_urls = get_urls(conn, author_ids, include_priority_values=True)
    wikipedia_urls = [z[1] for z in prioritized_urls if is_wikipedia_url(z[1])]

    gender, category = get_author_gender_from_wikipedia_pages(wikipedia_urls,
                                                              reference=author_names)

    if gender:
        return gender, 'wikipedia:%s' % (category)

    raw_urls = [z[1] for z in prioritized_urls]


    twitter_urls = get_twitter_urls(raw_urls)
    if not twitter_urls:
        logging.warning('No Twitter link(s) for %s' % (author_names))
    for twitter_url in twitter_urls:
        gender = get_gender_from_twitter_bio(twitter_url)
        if gender:
            return gender, 'twitter:Bio at %s' % (twitter_url)

    # TODO: lots to make this less sucky:
    # * Pull out the alternate names in ISFDB (this may be being done already,
    #   I'm not sure) - in particular I suspect lots of initialized names have
    #   the full name in ISFDB
    # * Use the proper columns in ISFDB for given/first name (I think there is
    #   one?)
    # * Try to use non-first names e.g. "A. Bertram Chandler"
    for name in author_names:
        gender = derive_gender_from_name(name.split(' ')[0])
        if gender:
            return gender, 'human-names'

    return None, category


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
    if not author_ids:
        raise AmbiguousArgumentsError('Do not know author "%s"' % (author_names))
    return get_author_gender_from_ids(conn, author_ids, author_names=author_names)


if __name__ == '__main__':
    # logging.getLogger().setLevel(logging.DEBUG)
    args = parse_args(sys.argv[1:],
                      description="Return an author's gender (if known)",
                      supported_args='av')

    conn = get_connection()
    gender, source = get_author_gender(conn, args.exact_author)
    print('%s (source: %s)' % (gender, source))
