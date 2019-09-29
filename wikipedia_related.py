#!/usr/bin/env python3
"""
Use Wikipedia categories if possible to determine an author's gender (TODO: or
other attributes e.g. nationality as best we can determine)

Extracted from author_gender.py - there should be no explicit references to
ISFDB in this module.
"""


# from collections import Counter
import logging
import pdb
import re
import sys

from bs4 import BeautifulSoup

from downloads import (download_file_only_if_necessary, UnableToSaveError)

def is_wikipedia_url(url, lang='en'):
    if lang:
        domain = '%s.wikipedia.org' % (lang)
    else:
        domain = 'wikipedia.org'
    return domain in url

def get_wikipedia_urls(urls):
    # I think this is no longer in use? (Because we didn't want the sorting,
    # as it borked prioritization done elsewhere.)

    wiki_urls = [z for z in urls if is_wikipedia_url(z)]
    # Sort by length so that we prefer 'http://en.wikipedia.org/wiki/Andre_Norton'
    # over'http://en.wikipedia.org/wiki/Andre_Norton_bibliography'.  This may
    # need further tuning if/when we come across more entries with multiple
    # Wikipedia URLs.  (This might also be good for supporting non en wikis too?)
    return sorted(wiki_urls, key=len)

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
    # Keep these in alphabetic order to retain sanity
    JOBS = ['artist',
            'blogger',
            'comedian', 'composer',
            'dramatist',
            'essayist',
            'feminist', 'film actor',
            'illustrator',
            'journalist',
            'novelist',
            'painter', 'people', 'playwright', 'poet',
            'radio actor',
            'screenwriter', 'singer', 'suicide',
            'writer']

    JOB_REGEX_BIT = '(%s)s?' % ('|'.join(JOBS))
    # GENDER_REGEXES is a list rather than a dict so that we can preserve
    # ordering, in case this is useful.  (Possibly easier than trying to get
    # regexes matching 100% perfectly in some cases?)
    # TODO (maybe): generic/group pseudonyms e.g. 'stratemeyer syndicate pseudonyms'
    GENDER_REGEXES = [
        ['X', ['non.binary %s' % (JOB_REGEX_BIT),
               'genderqueer %s' % (JOB_REGEX_BIT)]],
        ['F', ['(female|women|lesbian) (short story |comics |mystery )?%ss?$' % JOB_REGEX_BIT,
               '(actresses)$',
               '(female|women|lesbian) (science fiction and fantasy |speculative fiction )%ss?$' % JOB_REGEX_BIT,
               'transgender and transsexual women$'
               ]],
        ['M', ['transgender and transsexual men$',
               '^male (\w+ )?%ss?' % JOB_REGEX_BIT,
               '^male (speculative fiction )?%ss?' % JOB_REGEX_BIT,
               ' male (short story |non.fiction |speculative.fiction )%ss?$' % JOB_REGEX_BIT,
               ' male %ss?$' % JOB_REGEX_BIT
            ]]
    ]

    for gender, regexes in GENDER_REGEXES:
        for regex in regexes:
            for cat in categories:
                if re.search(regex, cat, re.IGNORECASE):
                    return gender, cat


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



if __name__ == '__main__':
    # This isn't really something you'd want to run standalone
    for url in sys.argv[1:]:
        gender, source = get_author_gender_from_wikipedia_pages([url], url)
        print('%s (source: %s)' % (gender, source))
