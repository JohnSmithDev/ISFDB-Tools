#!/usr/bin/env python3
"""
Tools for reporting/analysing the contents of a title - specifically in the
context of anthologies and collections, but potentially also magazines.

Coming back to this several months after it was originally written, I'm not sure why this
wasn't done as an enhancement to anthology_contents.py, which seems to cover similar ground...
"""


from collections import defaultdict, Counter
import pdb
import sys


from sqlalchemy.sql import text

from common import get_connection
from title_publications import get_publications_for_title_ids
from author_aliases import AuthorIdAndName

class NoContentsFoundError(Exception):
    pass

# Generally you want to exclude these from the return value of get_pub_contents
# TODO: add MAGAZINE and EDITOR?
CONTAINER_TITLE_TYPES = {'CHAPBOOK', 'COLLECTION', 'ANTHOLOGY'}


def get_pub_contents(conn, pub_ids, exclude_container_types=True):
    """
    Given a list/whatever of pub_ids, return a defaultdict mapping pub_id
    to the ordered contents of that publication
    """
    # Note that this will sort the page numbers alphabetically, so you'll get
    # 1, 10, 100, 2, 3 etc, which is of minimal use.

    query = text("""SELECT pc.pub_id, pc.pubc_page,
           t.title_id, t.title_title, CAST(t.title_copyright AS CHAR) title_date,
           t.title_ttype, t.title_storylen, t.title_parent, n.note_note
    FROM pub_content pc
    LEFT OUTER JOIN titles t ON pc.title_id = t.title_id
    NATURAL LEFT OUTER JOIN notes n
    WHERE pc.pub_id in :pub_ids
    ORDER BY pc.pub_id, pc.pubc_page, t.title_title;""")

    results = conn.execute(query, {'pub_ids': pub_ids})
    ret = defaultdict(list)
    for row in results:
        t_type = row.title_ttype
        if not (exclude_container_types and \
           t_type in CONTAINER_TITLE_TYPES):
            ret[row.pub_id].append(dict(row._mapping))

    if len(ret) == 0:
        raise NoContentsFoundError('No contents found in pubs (%s)' %
                                   (', '.join((str(z) for z in pub_ids))))

    # And now get the authors.  We could do this as part of the previous query,
    # but it could get messy when you have multiple authors.  This way also
    # avoids duplicating effort for the same titles that appear in multiple
    # pubs (which could well be all of them)
    title_ids = set()
    for contents in ret.values():
        title_ids.update([z['title_id'] for z in contents])
    title_to_authors = get_title_authors(conn, title_ids)

    # And now enhance the return dict with the authors
    for row in ret.values():
        for title in row:
            tid = title['title_id']
            title['authors'] = title_to_authors[tid]

    return ret


def get_title_authors(conn, title_ids):
    """
    Given a list/whatever of title_ids, return a dict mapping title_id to
    a list of (author_id, author_name) tuples.

    This similar to title_related.get_authors_for_title(), but handles multiple
    titles in a single query.  TODO: make those use common code?
    """
    query = text("""SELECT ca.title_id, ca.author_id, author_canonical
    FROM canonical_author ca
    LEFT OUTER JOIN authors a ON a.author_id = ca.author_id
    WHERE ca.title_id in :title_ids
    ORDER BY ca.title_id, a.author_id;""")

    # Cast title_ids to a list because SQLAlchemy/MySQL doesn't like sets
    results = conn.execute(query, {'title_ids': list(title_ids)})
    ret = defaultdict(list)
    for row in results:
        author_stuff = AuthorIdAndName( row.author_id, row.author_canonical)
        ret[row.title_id].append(author_stuff)
    return ret

def analyse_pub_contents(pub_contents, output_function=print):
    """
    Given a dict mapping pub_ids to a list of contents of each pub,
    optionally render summaries of the content of each pub,
    and return the one which looks the most complete.
    """
    best_metric = 0
    best = None
    appearances = Counter()
    for i, (pub_id, clist) in enumerate(pub_contents.items()):

        # Length of contents is a simplistic metric - it goes wrong on stuff
        # like the Le Guin Real and Unreal collection, where the pub that has
        # both volumes will beat the individual volumes
        if len(clist) > best_metric:
            best_metric = len(clist)
            best = (pub_id, clist)

        if i > 0:
            output_function()
        type_counts = Counter([z['title_ttype'] for z in clist])
        sf_type_counts = Counter([z['title_storylen'] or 'unknown' for z in clist
                                 if z['title_ttype'] == 'SHORTFICTION'])

        output_function(f'= Pub #{pub_id} stats =')
        for t_type, c in type_counts.most_common():
            output_function('* %-40s : %4d' % (t_type, c))
        for sft_type, c in sf_type_counts.most_common():
            output_function('* %-40s : %4d' % (sft_type, c))
    return best

def render_pub(pub_id, contents, output_function=print):
    print(f'= Publication #{pub_id} =')
    for content_number, c in enumerate(contents, 1):
        print(f'* {content_number}. {c}')

def get_title_contents(conn, title_ids, excluded_pub_types=None):
    # Note: this next function will return empty if you have a title ID for
    # a parent author (e.g. "Brian W. Aldiss") where the pubs only exist for
    # a title associated with variant author (e.g. "Brian Aldiss").
    # (See get_all_related_title_ids() for a way to work around that)

    if not excluded_pub_types:
        excluded_pub_types = set()

    publications = get_publications_for_title_ids(conn, title_ids)
    # print(publications)
    pub_to_stuff = {z['pub_id']: z for z in publications
                    if z['pub_ctype'] not in excluded_pub_types}
    # print(pub_to_stuff)
    pub_ids = list(pub_to_stuff.keys())
    # print(pub_ids)
    pub_contents = get_pub_contents(conn, pub_ids)
    return pub_contents



if __name__ == '__main__':
    # This is just for quick hacks/tests, not intended for "real" use
    conn = get_connection()

    P = """
    pub_ids = [int(z) for z in sys.argv[1:]]
    pub_contents = get_pub_contents(conn, pub_ids)
    """
    title_ids = [int(z) for z in sys.argv[1:]]
    pub_contents = get_title_contents(conn, title_ids)

    BASIC_RENDER = """
    for pub_number, (pub_id, clist) in enumerate(pub_contents.items()):
        if pub_number > 0:
            print()
        print(f'= {pub_id} =')
        for content_number, c in enumerate(clist, 1):
            print(f'* {content_number}. {c}')
    """
    best_pub_id, best_contents = analyse_pub_contents(pub_contents)
    render_pub(best_pub_id, best_contents)

