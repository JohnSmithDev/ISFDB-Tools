#!/usr/bin/env python
"""
Show all the different formats and countries a book was published in.


(The script name is a bit of misnomer.  TODO: rename it.)

TODO: Clean up this right mess, in large part due to confusiom over parent and
child IDs.


"""

from argparse import ArgumentParser
from datetime import date
from collections import namedtuple, defaultdict
import logging
import pdb
import re
import sys

from sqlalchemy.sql import text

from country_related import (derive_country_from_price, get_country)
from common import (get_connection, parse_args,
                    get_filters_and_params_from_args,
                    AmbiguousArgumentsError)
from isfdb_utils import convert_dateish_to_date
from author_aliases import get_author_aliases
from title_related import get_title_ids

AuthorBook = namedtuple('AuthorBook', 'author, book')

UNKNOWN_COUNTRY = 'XX'

class xxx_AmbiguousResultsError(Exception):
    pass

xxx_DEFAULT_TITLE_TYPES = ('NOVEL', 'CHAPBOOK', 'ANTHOLOGY', 'COLLECTION', 'SHORTFICTION')

def xxx_discover_title_details(conn, author_variations, title_variations,
                           extra_columns=None, exact_match=True,
                           title_types=None,
                           try_even_more_variations=True):
    """
    Try multiple combinations of author and title until we find a match.
    Returns either a single row if exact_match==True, or a list of matching
    rows if exact_match==False (which could be a list with one member), or
    None if nothing could be found
    """
    if try_even_more_variations:
        authors = []
        for author in author_variations:
            authors.extend(get_author_aliases(conn, author))
    else:
        authors = author_variations


    for author in authors:
        for title in title_variations:
             title_args = parse_args(['-A', author, '-T', title],
                                description='whatever')
             results = get_title_details(conn, title_args, extra_columns,
                                         title_types=title_types)
             if results:
                 if exact_match:
                     if len(results) == 1:
                         return results[0]
                     else:
                         raise AmbiguousResultsError('Search for %s/%s had %d matches' % (
                             author, title, len(results)))
                 else:
                     return results
    return None # Q: Would raising be better?


def xxx_get_all_title_details(conn, filter_args, extra_columns=None, title_types=None):
    return get_title_details(conn, filter_args, extra_columns, title_types,
                             postprocess=False)

def xxx_get_title_details(conn, filter_args, extra_columns=None, title_types=None,
                      postprocess=True):
    """
    Return a dictionary mapping title_id to dict of matching book(s),
    with (some) duplicate/irrelevant entries removed
    """

    if extra_columns:
        extra_col_str = ', ' + ', '.join(extra_columns)
    else:
        extra_col_str = ''
    fltr, params = get_filters_and_params_from_args(filter_args)
    params['title_types'] = title_types or DEFAULT_TITLE_TYPES

    details = fetch_title_details(conn, fltr, params, extra_col_str)
    if postprocess:
        return postprocess_titles(details)
    else:
        return details


def xxx_fetch_title_details(conn, fltr, params, extra_col_str):
    """
    This has been extracted from get_title_details primarily for easier testing
    w.r.t. not having to mock an arguments object.

    TODO(maybe): prefix this with an underscore?
    """

    # print(params)

    # This query isn't right - it fails to pick up "Die Kinder der Zeit"
    # The relevant ID is 1856439, not sure what column name that's for
    # Hmm, that's the correct title_id, perhaps there's more to it...

    # https://docs.sqlalchemy.org/en/latest/core/tutorial.html#using-textual-sql

    # The ORDER BY is just to ensure consistency/ease of testing
    query = text("""select t.title_id, author_canonical author, title_title title, title_parent
        %s
      from titles t
      left outer join canonical_author ca on ca.title_id = t.title_id
      left outer join authors a on a.author_id = ca.author_id
      WHERE %s AND
        title_ttype in :title_types
      ORDER BY title_id""" % (extra_col_str, fltr))


    #print(query)
    #print(params)

    return conn.execute(query, **params).fetchall()



def xxx_get_title_details_from_id(conn, title_id, extra_columns=None,
                              parent_search_depth=0):
    """
    Return either the matching row, or None.

    Set parent_search_depth to non-zero if you want parent (or grandparent etc)
    records instead)
    """
    # TODO: merge/refactor common bits in get_title_details
    if extra_columns:
        extra_col_str = ', ' + ', '.join(extra_columns)
    else:
        extra_col_str = ''


    query = text("""SELECT t.title_id, author_canonical author, title_title title, title_parent
        %s
      FROM titles t
      LEFT OUTER JOIN canonical_author ca ON ca.title_id = t.title_id
      LEFT OUTER JOIN authors a ON a.author_id = ca.author_id
      WHERE t.title_id = :title_id;""" % (extra_col_str))

    results = conn.execute(query, {'title_id': title_id}).fetchall()
    if results:
        res = results[0]
        if res['title_parent'] and parent_search_depth:
            return get_title_details_from_id(conn, res['title_parent'],
                                             extra_columns=extra_columns,
                                             parent_search_depth=parent_search_depth-1)
        return res
    else:
        return None

def xxx_postprocess_titles(title_rows):
    """
    Merge multiple title rows into a dict that maps title_id to details.
    This is for cases like books with multiple authors causing the SQL joins
    to return multiple rows.
    """
    results = list(title_rows)
    print(results)
    #title_ids = set([z[0] for z in results])
    title_ids = set([z['title_id'] for z in results])
    ret = []
    for bits in results:
        # Exclude rows that have a parent that is in the results (I think these
        # are typically translations).
        # No, An example is Girl with all the Gifts (title_id=166651) which
        # has parent of 1763907.  The only notable difference I can see is that
        # the latter is credited to Mike Carey rather than M.R. Carey, and as
        # a consequence that has all the series references.  (The fact it has
        # a higher title_id makes be dubious it's really a "parent")

        # Edit and "Way Down Dark" by J. P . Smythe (1866037, child) aka
        # James Smythe (1866038, parent) is similar, but has all the pubs
        # associated with the child instead.  This makes me think that
        # we have to search using all possible title_ids, hence changing the
        # argument in get_publications to be the list title_ids
        # http://www.isfdb.org/wiki/index.php/Schema:titles isn't much help

        # TODO: merge these into the returned results
        if not bits['title_parent'] and bits['title_parent'] not in title_ids:
            ret.append(bits)
    print(ret)
    return ret



def xxx_get_title_id(conn, filter_args, extra_columns=None, title_types=None):
    """
    This is a rework of the original get_title_id() to use the newer get_title_details()
    function.  It is likely that the stuff that calls this function could be easily
    changed to use get_title_details directly, making this redundant.  However,
    I don't want to look into that right now.
    """
    raw_data = get_title_details(conn, filter_args, extra_columns, title_types)
    ret = {}
    for bits in raw_data:
        ret[bits[0]] = AuthorBook(bits[1], bits[2])
    return ret


def xxx_get_all_related_title_ids(conn, title_id):
    """
    Given a title_id, return all parents and children.

    NB: A cursory check of the DB as of mid April 2019 indicates there are no
    grandparents or grandchildren
    """
    query = text("""SELECT t1.title_id, t1.title_parent,
                           t2.title_id, t2.title_parent,
                           t3.title_id, t3.title_parent
      FROM titles t1
      LEFT OUTER JOIN titles t2 ON t1.title_id = t2.title_parent
      LEFT OUTER JOIN titles t3 ON t1.title_parent = t2.title_id
      WHERE t1.title_id = :title_id;;;""")
    results = conn.execute(query, {'title_id': title_id}).fetchall()
    id_set = set()
    for row in results:
        id_set.update(row)
    # print(id_set)
    for ignorable in (0, None):
        try:
            id_set.remove(ignorable)
        except KeyError:
            pass
    return sorted(id_set)





def xxx_get_title_ids(conn, filter_args, extra_columns=None, title_types=None):
    """
    Get all relevant ids i.e. parent or child.
    TODO (nice-to-have): have the parent first in the returned list
    """
    raw_data = get_all_title_details(conn, filter_args, extra_columns, title_types)
    id_set = set()
    for row in raw_data:
        id_set.update(get_all_related_title_ids(conn, row[0]))
    return sorted(id_set)

    ORIGINAL_ATTEMPT = """
    raw_data = get_all_title_details(conn, filter_args, extra_columns, title_types)
    print(raw_data)
    parent = None
    children = set()
    for this_id, _, _, this_parent_id in raw_data:
        if this_parent_id:
            if parent and parent != this_parent_id:
                logging.warning('Multiple parentsfound?!? (child %d has parent %d != parent %d)' %
                                (this_id, this_parent_id, parent))
            else:
                parent = this_parent_id
        children.add(this_id)
    if parent:
        id_list = [parent]
    else:
        id_list = []
    id_list.extend(sorted(children))
    print('Returning %s' % (id_list))
    return id_list
    """


def get_publications(conn, title_ids, verbose=False):
    """
    This takes a list of title_ids because it seems we have to use both the
    child and the parent to be sure of finding matching pubs
    """
    query = text("""SELECT pub_ptype format,
                           CAST(pub_year AS CHAR) dateish,
                           pub_isbn isbn,
                           pub_price price,
                           pc.title_id title_id
      FROM pub_content pc
      LEFT OUTER JOIN pubs p ON p.pub_id = pc.pub_id
      WHERE pc.title_id IN :title_ids
        ORDER BY p.pub_year""")
    results = conn.execute(query, title_ids=title_ids)
    # pdb.set_trace()
    rows = list(results)
    ret = defaultdict(list)
    for row in rows:
        # print(row['pub_price'])
        ref = 'title_id=%d,ISBN=%s' % (row['title_id'], row['isbn'])
        country = derive_country_from_price(row['price'], ref=ref)
        if not country:
            if verbose:
                logging.warning('Unable to derive country fom price "%s"' %
                                row['price'])
            country = UNKNOWN_COUNTRY
        dt = convert_dateish_to_date(row['dateish'])
        ret[country].append((row['format'],
                             dt or None,
                             row['isbn'] or None))
    return ret




if __name__ == '__main__':
    args = parse_args(sys.argv[1:],
                      description='List publication countries and dates for a book',
                      supported_args='antv')

    conn = get_connection()
    FIRST_ATTEMPT = """
    title_id_dict = get_title_id(conn, args)
    if len(title_id_dict) > 1:
        raise AmbiguousArgumentsError('More than one book matching: %s' %
                                        ('; '.join([('%s - %s (%d)' % (bk[0], bk[1], idnum))
                                                     for idnum, bk in title_id_dict.items()])))
    elif not title_id_dict:
        raise AmbiguousArgumentsError('No books matching %s/%s found' %
                                        (args.author, args.title))

    title_id = title_id_dict.keys()[0]
    print(title_id)
    pubs = get_publications(conn, [title_id], verbose=args.verbose)
    """
    title_ids = get_title_ids(conn, args)
    if not title_ids:
        logging.error('No matching titles found')
        sys.exit(1)
    pubs = get_publications(conn, title_ids, verbose=args.verbose)
    # print(pubs)
    for country, details in pubs.items():
        print(country)
        for detail in details:
            print('%10s published %-12s (ISBN:%s)' % (detail))
