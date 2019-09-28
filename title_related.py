#!/usr/bin/env python
"""
Title-related functions extracted from publication_history.py

Some of these functions reference the authors table, perhaps they should
be moved elsewhere?

TODO: This is a mess due (mainly) to confusion over parent and child title
records.  A cleanup is much needed.
"""

from datetime import date
from collections import namedtuple, defaultdict
import logging
import pdb
import re
import sys

from sqlalchemy.sql import text

from common import (get_connection, parse_args,
                    get_filters_and_params_from_args,
                    AmbiguousArgumentsError)
from isfdb_utils import convert_dateish_to_date
from author_aliases import (get_author_aliases, AuthorIdAndName,
                            get_real_author_id_and_name)
from award_related import extract_authors_from_author_field

AuthorBook = namedtuple('AuthorBook', 'author, book')

class AmbiguousResultsError(Exception):
    pass

# Beware: the "mysql+mysqlconnector" driver doesn't support tuples or lists
# https://bugs.mysql.com/bug.php?id=89112
# Other connectors do however
DEFAULT_TITLE_TYPES = ('NOVEL', 'CHAPBOOK', 'ANTHOLOGY', 'COLLECTION', 'SHORTFICTION')

def discover_title_details(conn, author_variations, title_variations,
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


def get_all_title_details(conn, filter_args, extra_columns=None, title_types=None):
    return get_title_details(conn, filter_args, extra_columns, title_types,
                             postprocess=False)

def get_title_details(conn, filter_args, extra_columns=None, title_types=None,
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


def fetch_title_details(conn, fltr, params, extra_col_str):
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



def get_authors_for_title(conn, title_id):
    """
    Return an iterable of AuthorIdAndName tuples for a title.

    See get_definitive_authors() further down, which is conceptually similar,
    but more thorough, in terms of depseudonymization.
    """

    query = text("""SELECT a.author_id, author_canonical author
      FROM titles t
      LEFT OUTER JOIN canonical_author ca ON ca.title_id = t.title_id
      LEFT OUTER JOIN authors a ON a.author_id = ca.author_id
      WHERE t.title_id = :title_id;""")

    results = conn.execute(query, {'title_id': title_id}).fetchall()
    return [AuthorIdAndName(z.author_id, z.author) for z in results]


def get_title_details_from_id(conn, title_id, extra_columns=None,
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


def postprocess_titles(title_rows):
    """
    Merge multiple title rows into a dict that maps title_id to details.
    This is for cases like books with multiple authors causing the SQL joins
    to return multiple rows.
    """
    results = list(title_rows)
    # print(results)
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
    # print(ret)
    return ret



def get_title_id(conn, filter_args, extra_columns=None, title_types=None):
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


def get_all_related_title_ids(conn, title_id, only_same_types=True):
    """
    Given a title_id, return all parents and children.
    only_same_types avoids for example matching OMNIBUS to NOVELs, set to
    False if you want anything to be OK.

    NB: A cursory check of the DB as of mid April 2019 indicates there are no
    grandparents or grandchildren
    """

    if only_same_types:
        type_check1 = ' AND t1.title_ttype = t2.title_ttype '
        type_check2 = ' AND t1.title_ttype = t3.title_ttype '
    else:
        type_check1 = type_check2 = ''

    query = text("""SELECT t1.title_id, t1.title_parent,
                           t2.title_id, t2.title_parent,
                           t3.title_id, t3.title_parent
      FROM titles t1
      LEFT OUTER JOIN titles t2 ON t1.title_id = t2.title_parent %s
      LEFT OUTER JOIN titles t3 ON t1.title_parent = t2.title_id %s
      WHERE t1.title_id = :title_id;""" % (type_check1, type_check2))
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


def get_title_ids(conn, filter_args, extra_columns=None, title_types=None):
    """
    Get all relevant ids i.e. parent or child.
    TODO (nice-to-have): have the parent first in the returned list
    """
    raw_data = get_all_title_details(conn, filter_args, extra_columns, title_types)
    id_set = set()
    for row in raw_data:
        id_set.update(get_all_related_title_ids(conn, row[0]))
    return sorted(id_set)




def get_definitive_authors(conn, book):
    """
    Given a book object - basically, anything with
    * ideally a "title_id" attribute
    * failing that, an "author" (name) attribute
    return a list of tuples containing (author_id, author_name) for each
    author.

    For the returned tuples:
    * author_id may be None, for "authors" who don't have proper ISFDB records
      (this should only affect "books" derived from the awards table, usually
       for "multimedia" awards like the Tiptree).
    * author_name should be the real name of the author (where known), which
      may not be the same as the credited author e.g. "Mira Grant"=>"Seanan McGuire"

    See get_authors_for_title() for a simpler function that doesn't do
    any depseudonymization.
    """
    try:
        if not book.title_id:
            raise AttributeError('title_id==0 is essentially no title_id')
        credited_author_stuff = get_authors_for_title(conn, book.title_id)
        real_author_stuff = []
        for credited_author in credited_author_stuff:
            author_stuff = get_real_author_id_and_name(conn, credited_author.id)
            if author_stuff:
                # Replace this apparent pseudonym with these real author(s)
                real_author_stuff.extend(author_stuff)
            else:
                # Credited author was real, so keep it
                real_author_stuff.append(credited_author)

        # Report discrepancies between the newer title_id->author_ids method
        # versus the original author_names method
        if not credited_author_stuff and not book.author:
            pass # Don't worry about set() != set('') e.g. AO3 on Best Related
        else:
            # author_names_1 = set([z.name for z in credited_author_stuff])
            author_names_1 = set([z.name for z in real_author_stuff])
            author_names_2 = set(extract_authors_from_author_field(book.author))
            author_diffs = author_names_1.symmetric_difference(author_names_2)
            if author_diffs:
                logging.warning('title_id (%d) authors != author_names (%s != %s)' %
                            (book.title_id, author_names_1, author_names_2))
        # Regardless of any differences, use the author_id way if possible -
        # as these are a tuple with author names, we can still fall back to those
        author_bits = real_author_stuff
    except AttributeError:
        # No title_id attribute

        # Thought: perhaps it might be more elegant to fake the id/name tuple
        # with id=0 or None here - that would make the code below cleaner?
        # TODO: I think this counts both real names and aliases, which is
        # wrong - we should count one or the other, not both

        # Get a list of author names
        author_names = extract_authors_from_author_field(book.author)
        # Turn it into fake AuthorIdAndName namedtuple
        author_bits = [AuthorIdAndName(None, z) for z in author_names]

    return author_bits

