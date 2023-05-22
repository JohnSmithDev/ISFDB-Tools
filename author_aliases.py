#!/usr/bin/env python3
"""
This is primarily intended as a library module for other scripts, but there's
a perfunctory standalone functionality that may be of use.
"""

from collections import namedtuple
import logging
import pdb
import re
import sys

from sqlalchemy.sql import text

from common import get_connection

AuthorIdAndName = namedtuple('AuthorIdAndName', 'id, name')

def unlegalize(txt):
    """
    Given a name of the form "Bloggs, Joe", return "Joe Bloggs"

    See tests for some (commented out) examples that aren't properly catered
    for right now.
    """
    if not txt or ',' not in txt:
        return txt
    else:
        bits = txt.split(',')
        if len(bits) == 2:
            return '%s %s' % (bits[1].strip(), bits[0].strip())
        elif len(bits) == 3:
            # Mostly of the form 'Rigney, James Oliver, Jr.' - but there other
            # patterns that I can't be bothered with
            return '%s %s %s' % (bits[1].strip(), bits[0].strip(), bits[2].strip())
        else:
            # Bloody aristocrats - they can sod off
            return None


def get_author_aliases(conn, author, search_for_additional_pseudonyms=True):
    """
    Author can be a text string or an integer, the latter indicating an author_id.

    Return all aliases, pseudonyms, alternate spellings, etc for an author.
    This originally returned a set of names, it now returns a list, ordered
    (roughly) by how much the names resemble the supplied name.

    If a pseudonym is provided, then by default a second query will be done on
    the real/canonical/primary name to pick up any other pseudonums.  Set
    search_for_additional_pseudonyms to False if you don't want this extra lookup,
    at the risk of missing out on all pseudonyms.
    """

    if isinstance(author, int):
        fltr = 'a1.author_id = :author'
    else:
        fltr = 'a1.author_canonical = :author OR a1.author_legalname = :author'

    primary_name = None

    # This would be much nicer if I had a newer MySQL/Maria with CTEs...
    # The two lots of joins are because we don't know if we have been given
    # a real name or an alias, so we try going "in both directions".
    query = text("""SELECT -- a1.author_id id1,
                    a1.author_canonical name1, a1.author_legalname legal1,
                    -- p.pseudonym, a2.author_id id2,
                    a2.author_canonical name2, a2.author_legalname legal2,
                    a3.author_canonical name3, a3.author_legalname legal3

  FROM authors a1
  left outer join pseudonyms p1 on p1.author_id = a1.author_id
  left outer join authors a2 on p1.pseudonym = a2.author_id
  left outer join pseudonyms p2 on p2.pseudonym = a1.author_id
  left outer join authors a3 on p2.author_id = a3.author_id
    where %s;""" % (fltr))
    params = {'author': author}
    results = conn.execute(query, params).fetchall()
    ret = set()
    for row in results:
        if row.name3:
            if primary_name:
                logging.warning('Not sure if %s or %s is the primary name?!' %
                                (primary_name, row.name3))
            else:
                primary_name = row.name3
        for col in ('name1', 'name2', 'name3'):
            if row._mapping[col]:
                ret.add(row._mapping[col])
        for col in ('legal1', 'legal2', 'legal3'):
            if row._mapping[col]:
                legal = unlegalize(row._mapping[col])
                if legal:
                    ret.add(legal)

    if not primary_name:
        # The name supplied should be the primary name, so no need to do another
        # lookup
        pass
    elif search_for_additional_pseudonyms:
        # print(f'Before: {ret}')
        ret.update(get_author_aliases(conn, primary_name,
                                      search_for_additional_pseudonyms=False))
        # print(f'After: {ret}')

    if isinstance(author, int):
        # Pass dummy value for resemblance sorting
        return order_aliases_by_name_resemblance('', ret)
    else:
        return order_aliases_by_name_resemblance(author, ret)

def order_aliases_by_name_resemblance(author, aliases):
    # The following functions and sorting are an attempt to return the most
    # relevant names first - this is to minimize the risk of having authors
    # who used house pseudonyms having the latter being prioritized (e.g.
    # Bruce Holland Rogers => Victor Appleton).  It could be much improved in
    # terms of efficiency (e.g. use caching) or effectiveness (have some logic
    # for initials matching names), but this may be good enough for now.
    def name_words(name):
        return set([z.lower() for z in re.split(r'\W', name) if z])
    author_name_words = name_words(author)
    def word_difference(name):
        # The second value in the returned tuple is just to ensure consistency
        # (mainly for tests) when 2 names have the same score
        this_words = name_words(name)
        return (len(this_words.symmetric_difference(author_name_words)),
                name)

    return sorted(aliases, key=word_difference)

def get_gestalt_ids(conn, ids_to_check, more_than=2):
    """
    Given a list/iterable/whatever of IDs, return a list of any that are
    pseudonyms used by more than the specified value.
    """
    query = text("""SELECT pseudonym FROM
    (
      SELECT pseudonym, COUNT(1) num_uses
      FROM pseudonyms
      WHERE pseudonym in :ids_to_check
      GROUP BY pseudonym
    ) foo
    WHERE foo.num_uses > :more_than ;""")
    results = conn.execute(query, {'ids_to_check': ids_to_check,
                                   'more_than': more_than}).fetchall()
    return [z.pseudonym for z in results]


def _get_author_alias_tuples(conn, author, ignore_gestalt_threshold=None,
                             comparison_name=None):
    """
    Helper function for _get_author_alias_ids, basically for supporting the
    secondary lookup if a pseudonym was supplied.
    """
    # This would be much nicer if I had a newer MySQL/Maria with CTEs...
    # The two lots of joins are because we don't know if we have been given
    # a real name or an alias, so we try going "in both directions".
    query = text("""SELECT a1.author_id id1, a1.author_canonical author1,
          a2.author_id id2, a2.author_canonical author2,
          a3.author_id id3, a3.author_canonical author3
  FROM authors a1
  left outer join pseudonyms p1 on p1.author_id = a1.author_id
  left outer join authors a2 on p1.pseudonym = a2.author_id
  left outer join pseudonyms p2 on p2.pseudonym = a1.author_id
  left outer join authors a3 on p2.author_id = a3.author_id
  where a1.author_canonical = :author
     or a1.author_legalname = :author;""")
    params = {'author': author}
    results = conn.execute(query, params).fetchall()

    # Uggh, horrible copypasting from above
    def name_words(name):
        return set([z.lower() for z in re.split('\W', name) if z])

    author_name_words = name_words(comparison_name or author)

    def word_difference(name):
        # The second value in the returned tuple is just to ensure consistency
        # (mainly for tests) when 2 names have the same score
        this_words = name_words(name)
        return (len(this_words.symmetric_difference(author_name_words)),
                name)
    id_to_name = {} # Use a dict so that any duplicate IDs overwrite each other

    primary_name = None

    for row in results:
        # print(row)
        possible_primary_name = row.author3
        if possible_primary_name:
            if primary_name:
                logging.warning('Not sure if %s or %s is the primary name?!' %
                                (primary_name, possible_primary_name))
            else:
                primary_name = possible_primary_name

        for i, author_id in enumerate(row[::2]):
            if author_id: # Skip 0/None/null values
                id_to_name[author_id] = word_difference(row[(i*2)+1])

    return id_to_name, primary_name


def get_author_alias_ids(conn, author, ignore_gestalt_threshold=None,
                         search_for_additional_pseudonyms=True):
    """
    Return all [*] IDs for an author, inc.  pseudonyms, alternate spellings, etc
    Basically the same query as get_author_aliases, just returning different
    values.

    Optionally set ignore_gestalt_threshold to ignore pseudonyms used by more
    than the specified value, suggestion is 2 if this is used.  (There'll be an
    extra database call if a value is passed for this.)

    If a pseudonym is provided, then by default a second query will be done on
    the real/canonical/primary name to pick up any other pseudonums.  Set
    search_for_additional_pseudonyms to False if you don't want this extra lookup,
    at the risk of missing out on all pseudonyms.

    TODO (probably): merge common code from get_author_aliases - although that's
    more likely to happen in the helper function above.

    """

    id_to_name, primary_name = _get_author_alias_tuples(conn, author,
                                                        ignore_gestalt_threshold)
    if not primary_name:
        # The name supplied should be the primary name, so no need to do another
        # lookup
        pass
    elif search_for_additional_pseudonyms:
        # print(f'Before: {id_to_name}')
        # Passing comparison_name arg ensures we do a "diff" against the supplied
        # name, not the real/primary name - this means the diff values are
        # consistent for sorting a few lines down.
        more_mappings, _ = _get_author_alias_tuples(conn, primary_name,
                                                    ignore_gestalt_threshold,
                                                    comparison_name=author)
        id_to_name.update(more_mappings)
        # print(f'After: {id_to_name}')


    # This sorting is so that the IDs for the most similar names appear first
    sortable_id_tuples = id_to_name.items()
    sorted_id_tuples = sorted(sortable_id_tuples, key=lambda z: z[1])
    sorted_ids = [z[0] for z in sorted_id_tuples]

    if ignore_gestalt_threshold is not None:
        ids_to_ignore = set(get_gestalt_ids(conn, sorted_ids, ignore_gestalt_threshold))
        # print(f'Ignoring {ids_to_ignore}')
        return [z for z in sorted_ids if z not in ids_to_ignore]
    else:
        return sorted_ids

    ORIG = """
    ret = set()
    for row in results:
        ret.update(row)
    for ignore in (0, None):
        try:
            ret.remove(ignore)
        except KeyError:
            pass
    return sorted(ret)
    """

def get_real_author_id(conn, pseudonym_id):
    """
    Given a numeric pseudonym_id - which is a author_id in any other context/table -
    return a list of the "real" author_ids, or None if this is the "real" ID.

    This was the original function, before I realized I needed the name as well
    in the context of the overall problem I was trying to solve.  As such this
    function is maybe pointless - worth noting that it'll be doing an extra JOIN
    that's not needed if all you care about is the ID.
    """
    results = get_real_author_id_and_name(conn, pseudonym_id)
    if not results:
        return None
    return [z.id for z in results]


def get_real_author_id_and_name(conn, pseudonym_id):
    """
    Given a numeric pseudonym_id - which is a author_id in any other context/table -
    return a list of the "real" author_ids, or None if this is the "real" ID.

    """
    query = text("""SELECT p.author_id, a.author_canonical name
    FROM pseudonyms p
    LEFT OUTER JOIN authors a ON (a.author_id = p.author_id)
    WHERE p.pseudonym = :pseudonym_id
    ORDER BY author_id;""") # The ORDER BY is just for consistency/ease of testing
    params = {'pseudonym_id': pseudonym_id}
    results = conn.execute(query, params).fetchall()
    if results:
        return [AuthorIdAndName(z.author_id, z.name) for z in results]
    else:
        return None


def get_real_author_id_and_name_from_name(conn, pseudonym):
    """
    Same as get_real_author_id_and_name, but takes a name string rather than a
    numeric ID
    """
    # r_details = details about the real/canonical entry
    # p_pdetails = details about the real/canonical entry
    query = text("""SELECT r_details.author_id, r_details.author_canonical name
    FROM pseudonyms p
    LEFT OUTER JOIN authors p_details ON (p_details.author_id = p.pseudonym)
    LEFT OUTER JOIN authors r_details ON (r_details.author_id = p.author_id)
    WHERE p_details.author_canonical = :pseudonym
    ORDER BY author_id;""") # The ORDER BY is just for consistency/ease of testing

    params = {'pseudonym': pseudonym}
    results = conn.execute(query, params).fetchall()
    if results:
        return [AuthorIdAndName(z.author_id, z.name) for z in results]
    else:
        # Maybe this is a real ID then?
        # (This could probably be done as part of the query above, but I'm too
        # lazy to try to get my head around it right now)
        query2 = text("""SELECT author_id, author_canonical name
        FROM authors
        WHERE author_canonical = :pseudonym""")
        params = {'pseudonym': pseudonym}
        results2 = conn.execute(query2, params).fetchone()

        # print(pseudonym, results2, results2.author_id, results2.name)
        if results2:
            return [AuthorIdAndName(results2.author_id, results2.name)]
        else:
            return None


def get_author_name(conn, author_id):
    """
    Return the author name for the given author_id

    This isn't intended as a function that's useful in production; rather, it
    has been created as a testbed for understanding differences in returned values
    for non-ASCII names that I'm seeing on different machines (with different
    versions of Python, MariaDB, etc).

    Note that this won't actually do anything with the aliases/pseudonyms!
    """
    query = text("""SELECT author_canonical
    FROM authors
    WHERE author_id = :author_id;""")
    params = {'author_id': author_id}
    result_thing = conn.execute(query, params)
    result = result_thing.fetchone()
    return result[0]

if __name__ == '__main__':
    mconn = get_connection()
    """
    for i, name in enumerate(sys.argv[1:]):
        try: # Convert to int if it is numeric
            name = int(name)
        except ValueError: # otherwise leave as-is
            pass
        aliases = get_author_aliases(mconn, name)
        if len(sys.argv) > 2:
            print('= %s =' % (name))
        if aliases:
            for al in aliases:
                print(al)
        else:
            print('<No known aliases/variant names>')
        if len(sys.argv) > 2 and i < len(sys.argv) - 1:
            print('\n')
    """
    a_id = int(sys.argv[1])
    author_name = get_author_name(mconn, a_id)
    print('%s' % (author_name))
    # I think the following stuff is just Unicode/non-ASCII related
    print('%s' % (type(author_name)))
    print('-'.join([str(ord(z)) for z in author_name]))
    print([(z, ord(z)) for z in author_name])


