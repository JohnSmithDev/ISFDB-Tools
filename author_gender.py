#!/usr/bin/env python3
"""
Use Wikipedia categories if possible to determine an author's gender.
"""


import logging
import pdb
import re
import sys

from sqlalchemy.sql import text
from bs4 import BeautifulSoup

from common import (get_connection, parse_args, AmbiguousArgumentsError)
from author_aliases import get_author_alias_ids
from downloads import download_file_only_if_necessary



def get_urls(conn, author_ids):
    # I'm not sure where ISFDB gets the "display label" for links from, I'm
    # guessing it's maybe hardcoded as some links don't have it e.g. a couple
    # for http://www.isfdb.org/cgi-bin/ea.cgi?20
    query = text("""SELECT author_id, url
    FROM webpages wp
    WHERE wp.author_id IN :author_ids;""")
    rows = conn.execute(query, {'author_ids':author_ids})
    return [z.url for z in rows]


def get_wikipedia_url(urls):
    wiki_urls = [z for z in urls if 'en.wikipedia.org' in z]
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

def determine_gender_from_categories(categories):
    for cat in categories:
        if re.search(' male (novelist|writer)s?$', cat, re.IGNORECASE):
            return 'M'
        elif re.search(' (female|women) (novelist|writer)s?$', cat, re.IGNORECASE):
            return 'F'
        elif re.search(' (lesbian) (novelist|writer)s?$', cat, re.IGNORECASE):
            return 'F'
        elif re.search('transgender and transsexual men$', cat, re.IGNORECASE):
            return 'M'
        elif re.search('transgender and transsexual women$', cat, re.IGNORECASE):
            return 'F'

    logging.warning('Unable to determine gender based on these categories: %s' %
                    (categories))
    return None


def get_author_gender(conn, author_names):
    """
    Returns 'M', 'F', 'X' (for other/nonbinary) or None (if unknown)
    """
    author_ids = get_author_alias_ids(conn, author_names)
    if not author_ids:
        raise AmbiguousArgumentsError('Do not know author "%s"' % (author_names))
    urls = get_urls(conn, author_ids)
    wiki_url = get_wikipedia_url(urls)
    if wiki_url:
        wiki_file = get_wikipedia_content(wiki_url)
        categories = extract_categories_from_content(wiki_file)
        gender = determine_gender_from_categories(categories)
        if gender:
            return gender
        else:
            logging.warning('No gender information found in %s' % (wiki_url))
            return None
    else:
        logging.warning('No Wikipedia link for %s/%s' % (author_names, author_ids))
        return None



if __name__ == '__main__':
    # logging.getLogger().setLevel(logging.DEBUG)
    args = parse_args(sys.argv[1:],
                      description="Return an author's gender (if known)",
                      supported_args='av')

    conn = get_connection()
    data = get_author_gender(conn, args.exact_author)
    print(data)
