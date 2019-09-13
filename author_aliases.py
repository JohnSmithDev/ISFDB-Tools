#!/usr/bin/env python3
"""
This is primarily intended as a library module for other scripts, but there's
a perfunctory standalone functionality that may be of use.
"""

import pdb
import re
import sys

from sqlalchemy.sql import text

from common import get_connection

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


def get_author_aliases(conn, author):
    """
    Return all [*] aliases, pseudonyms, alternate spellings, etc for an author.
    This originally returned a set of names, it now returns a list, ordered
    (roughly) by how much the names resemble the supplied name.

    [*] See commented example in the tests for a flaw in this - if given a
        pseudonym, this doesn't currently return other pseudonyms - e.g. results
        for "Robert Heinlein" vs "Robert A. Heinlein" are very different.
        Perhaps maybe instead do one lookup to exstablish the "official" author_id
        (which may well be the same as the supplied name), and then a second
        one to get all of its aliases?  (Or perhaps, a single query that
        effectively does that?)
    """

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
  where a1.author_canonical = :author
     or a1.author_legalname = :author;""")
    results = conn.execute(query, author=author).fetchall()
    # print(results)
    # pdb.set_trace()
    ret = set()
    for row in results:
        for col in ('name1', 'name2', 'name3'):
            if row[col]:
                ret.add(row[col])
        for col in ('legal1', 'legal2', 'legal3'):
            if row[col]:
                legal = unlegalize(row[col])
                if legal:
                    ret.add(legal)

    #if ret:
    #    print('%s => %s' % (author, ret))
    return order_aliases_by_name_resemblance(author, ret)

def order_aliases_by_name_resemblance(author, aliases):

    # The following functions and sorting are an attempt to return the most
    # relevant names first - this is to minimize the risk of having authors
    # who used house pseudonyms having the latter being prioritized (e.g.
    # Bruce Holland Rogers => Victor Appleton).  It could be much improved in
    # terms of efficiency (e.g. use caching) or effectiveness (have some logic
    # for initials matching names), but this may be good enough for now.
    def name_words(name):
        return set([z.lower() for z in re.split('\W', name) if z])
    author_name_words = name_words(author)
    def word_difference(name):
        # The second value in the returned tuple is just to ensure consistency
        # (mainly for tests) when 2 names have the same score
        this_words = name_words(name)
        return (len(this_words.symmetric_difference(author_name_words)),
                name)

    return sorted(aliases, key=word_difference)


def get_author_alias_ids(conn, author):
    """
    Return all [*] IDs for an author, inc.  pseudonyms, alternate spellings, etc
    Basically the same query as get_author_aliases, just returning different
    values.
    TODO (probably): merge common code from get_author_aliases.

    [*] See commented example in the tests for a flaw in this - if given a
        pseudonym, this doesn't currently return other pseudonyms - e.g. results
        for "Robert Heinlein" vs "Robert A. Heinlein" are very different.
        Perhaps maybe instead do one lookup to exstablish the "official" author_id
        (which may well be the same as the supplied name), and then a second
        one to get all of its aliases?  (Or perhaps, a single query that
        effectively does that?)
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
    results = conn.execute(query, author=author).fetchall()

    # Uggh, horrible copypasting from above
    def name_words(name):
        return set([z.lower() for z in re.split('\W', name) if z])
    author_name_words = name_words(author)
    def word_difference(name):
        # The second value in the returned tuple is just to ensure consistency
        # (mainly for tests) when 2 names have the same score
        this_words = name_words(name)
        return (len(this_words.symmetric_difference(author_name_words)),
                name)
    id_to_name = {} # Use a dict so that any duplicate IDs overwrite each other
    for row in results:
        # print(row)
        for i, author_id in enumerate(row[::2]):
            if author_id: # Skip 0/None/null values
                id_to_name[author_id] = word_difference(row[(i*2)+1])
    sortable_id_tuples = id_to_name.items()
    sorted_id_tuples = sorted(sortable_id_tuples, key=lambda z: z[1])
    return [z[0] for z in sorted_id_tuples]

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
    """
    query = text("""SELECT author_id
    FROM pseudonyms
    WHERE pseudonym = :pseudonym_id
    ORDER BY author_id;""") # The ORDER BY is just for consistency/ease of testing
    results = conn.execute(query, pseudonym_id=pseudonym_id).fetchall()
    if results:
        return [z.author_id for z in results]
    else:
        return None




if __name__ == '__main__':
    conn = get_connection()
    for i, name in enumerate(sys.argv[1:]):
        aliases = get_author_aliases(conn, name)
        if len(sys.argv) > 2:
            print('= %s =' % (name))
        if aliases:
            for al in aliases:
                print(al)
        else:
            print('<No known aliases/variant names>')
        if len(sys.argv) > 2 and i < len(sys.argv) - 1:
            print('\n')
