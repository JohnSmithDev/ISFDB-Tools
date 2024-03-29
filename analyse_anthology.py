#!/usr/bin/env python3
"""
Given a title ID of an anthology or collection, generate data about the contents

Example usages and useful examples:

  ./analyse_anthology.py 33629 (this one has all original content)
  ./analyse_anthology.py 2013507 (this one one reprint and the rest original)
  ./analyse_anthology.py 2305932 (a 2018 year's best)
  ./analyse_anthology.py 2267599 (single author collection)
  ./analyse_anthology.py 1655765 (this has a Tor.com chapbook vs magazine entry; two stories
         are title variant; one is an author name variant; one was first published in an online
         venue not tracked by ISFDB as of 2023-03-08)

BUG (possibly in code from elsewhere called from here): does not pick up prior serializations
e.g. https://www.isfdb.org/cgi-bin/title.cgi?2132040

"""

from collections import defaultdict, Counter
from lxml import html
import pdb
import re
import sys


from sqlalchemy.sql import text

from author_aliases import AuthorIdAndName
from common import get_connection
from magazine_canonicalization import CANONICAL_MAGAZINE_NAME, SHORT_MAGAZINE_NAME
from title_publications import (get_earliest_pub, get_title_editor_for_pub_id,
                                get_title_editor_for_title_id)
from title_contents import (get_title_contents, analyse_pub_contents, NoContentsFoundError)
from title_related import get_all_related_title_ids
from custom_exceptions import (UnexpectedTypeError, UnexpectedNumberOfRowsError)

ORIGIN_NOT_FOUND_MARKER = '*'

def do_nothing(*args, **kwargs):
    """Stub for output_function argument override"""
    pass

def get_filtered_title_contents(conn, title_id):
    """
    Get the contents, excluding stuff that isn't of interest such as artwork and introductions
    """
    # TODO: we should allow OMNIBUSES if title_id is itself an omnibus - although perhaps we
    # should be careful if this is an omnibus of say vols 1-3, and then there's a bigger
    # omnibus?  In practice, I don't think you'd use this code for omnibuses?
    pub_contents = get_title_contents(conn, [title_id], excluded_pub_types={'OMNIBUS'})
    best_pub_id, best_contents = analyse_pub_contents(pub_contents, output_function=do_nothing)
    return [z for z in best_contents
            if z['title_ttype'] not in {'ESSAY', 'COVERART', 'INTERIORART'}]



def get_container_title_id_for_pub(conn, pub_details):
    if pub_details['pub_ctype'] not in ('ANTHOLOGY', 'COLLECTION', 'CHAPBOOK', 'MAGAZINE',
                                        'NOVEL'):
        raise UnexpectedTypeError('Cannot get container title id for non container pub %d/%s' %
                                  (pub_details['pub_id'], pub_details['pub_ctype']))
    # Removed 'NOVEL' from the list of title_ttypes, as it breaks things when an anthology
    # contains a novel e.g. https://www.isfdb.org/cgi-bin/pl.cgi?774892
    # Perhaps there's a better/safer way to handle this situation?
    query = text("""SELECT title_id
    FROM pub_content pc
    NATURAL JOIN titles t
    WHERE pub_id = :pub_id
      AND title_ttype IN ('ANTHOLOGY', 'COLLECTION', 'EDITOR', 'CHAPBOOK');""")
    results = conn.execute(query, pub_details).fetchall()

    if len(results) != 1:
        raise UnexpectedNumberOfRowsError('Got %d titles (%s), returned for pub_id %d, expected 1' %
                        (len(results), [z['title_id'] for z in results],
                         pub_details['pub_id']))
    return results[0].title_id

def postprocess_publication_details(conn, pub_details, original_container_title=None):
    """
    Return a dictionary with processed publication details e.g. normalized magazine name,
    sanitisation of weird edge cases
    """

    # print(pub_details)

    ret = pub_details.copy()
    ret['processed_title'] = ret['pub_title']
    ret['original_pub_not_found'] = False

    if original_container_title:
        # Get the title_id associated with this pub, so we can compare them
        ret['title_id'] = get_container_title_id_for_pub(conn, pub_details)

    if pub_details['pub_series_name'] == 'A Tor.com Original':
        ret['pub_ctype'] = 'MAGAZINE'
        ret['publisher_name'] = 'Tor.com'
        ret['processed_title'] = 'Tor.com'
    elif pub_details['pub_ctype'] == 'MAGAZINE':
        magazine_details = get_title_editor_for_pub_id(conn, pub_details['pub_id'])
        if not magazine_details.series_id and magazine_details.title_parent:
            magazine_details = get_title_editor_for_title_id(conn, magazine_details.title_parent)

        ret['processed_title'] = magazine_details.series_title
    elif original_container_title and \
         original_container_title == ret['title_id']: # TODO (?) check variants
        ret['processed_title'] += ORIGIN_NOT_FOUND_MARKER
        ret['original_pub_not_found'] = True

    canon_title = CANONICAL_MAGAZINE_NAME.get(ret['processed_title'], ret['processed_title'])
    short_canon_title = SHORT_MAGAZINE_NAME.get(canon_title, canon_title)

    ret['short_title'] = short_canon_title

    return ret


def sanitized_title_type(t_dict):
    """
    Given a dictionary derived from the titles table, return the shortfiction type or the more
    general type as appropriate.
    """
    if t_dict['title_ttype'] == 'SHORTFICTION' and t_dict['title_storylen']:
        return t_dict['title_storylen']
    else:
        return t_dict['title_ttype'].lower()


def clean_up_extracted_pub(content):
    """
    Postprocess the extracted publication name from extracted_org_pub_from_note()
    """
    for zappable in ('^the web.zine,? *',):
        content = re.sub(zappable, '', content)

    # TODO: tidy this up as-and-when more examples of what needs doing have been found
    if content.lower().startswith('<i>'):
        # https://www.isfdb.org/cgi-bin/title.cgi?1871149
        bits = content[3:].split('<')
        txt = bits[0]
    else:
        txt = str(html.fromstring(content).text_content())

    for ch in ('.', '"'):
        if txt.endswith(ch):
            txt = txt[:-1]
    return txt


def extract_orig_pub_from_note(txt):
    """
    Given some note text, extract any details about original publication (of a short story),
    or return None.

    This will be an ongoing whac-a-mole to catch all the variants that people have used...
    """

    if not txt:
        return None

    # TODO more patterns (as and when I find them
    for pattern in ('(First|Originally) (appeared|published) (online at|in) (?P<this>.*)',
                    # 'First published in (?P<this>.*)',
                    '.*Originally published in (?P<this>.*)',
                    # 'Originally published in (?P<this>.*)',
                    'Originally published as a (?P<this>.*)'):
        if result := re.match(pattern, txt, re.IGNORECASE):
            # https://stackoverflow.com/questions/753052/strip-html-from-strings-in-python
            return clean_up_extracted_pub(result.group('this'))
    return None



def analyse_title(conn, title_id, output_function=print, sort_by_type_and_source=True):
    """
    Return (and optionally output) details about the contents of the specified title
    """

    ret = []

    try:
        contents = get_filtered_title_contents(conn, title_id)
        # print(contents)

        for content_stuff in contents:
            relevant_title_ids = get_all_related_title_ids(conn, content_stuff['title_id'],
                                                           only_same_languages=True)
            earliest = get_earliest_pub(conn, relevant_title_ids)
            details = postprocess_publication_details(conn, earliest,
                                                      original_container_title=title_id)
            ret.append((content_stuff, details))

            # print(content_stuff, details)
        if sort_by_type_and_source:
            ret.sort(key=lambda z: (z[1]['pub_ctype'], z[1]['short_title'], z[0]['title_title']))
        for (content_stuff, details) in ret:
            orig_pub = details['short_title']
            orig_type = details['pub_ctype']
            if details['original_pub_not_found']:
                if noted_original := extract_orig_pub_from_note(content_stuff['note_note']):
                    orig_pub = noted_original
                    orig_type = 'UNKNOWN'

            output_function('%-15s %40s was first published in %10s %s' % (
                sanitized_title_type(content_stuff),
                content_stuff['title_title'][:40],
                orig_type,
                orig_pub
            ))


    except NoContentsFoundError as err:
        output_function(f'<<{err}>>')
    return ret


if __name__ == '__main__':
    conn = get_connection()

    for t in sys.argv[1:]:
        analyse_title(conn, int(t))

