#!/usr/bin/env python3

from glob import glob
import logging
import os
import pdb
import re
import sys

from sqlalchemy.sql import text

from country_related import get_country
from common import (get_connection, parse_args, get_filters_and_params_from_args,
                    AmbiguousArgumentsError)


COUNTRY_HACK_DIR = os.path.join(os.path.dirname(__file__), 'country_hacks')
COUNTRY_OVERRIDES = glob(os.path.join(COUNTRY_HACK_DIR, '*'))

def load_hacks(filenames=None):
    if not filenames:
        filenames = COUNTRY_OVERRIDES
    # print(filenames)
    ret = {}
    for fn in filenames:
        try:
            with open(fn) as inputstream:
                for i, raw_line in enumerate(inputstream, 1):
                    line = re.sub('#.*$', '', raw_line).strip()
                    if not line:
                        continue
                    # print('%d [%s]' % (i, line))
                    try:
                        author, country = [z.strip() for z in line.split('=')]
                        ret[author] = country
                    except ValueError as err:
                        logging.error('Ignoring bad line %d in %s (%s)' %
                                      (i, fn, err))
        except FileNotFoundError as err:
            pass # This is a temp hack whilst the hack file is not in the repo
    return ret

def get_birthplaces_for_pseudonym(conn, author_id):
    """
    Examples:
    Mira Grant (author_id=133814) is Seanan McGuire (129348)
    James S. A. Corey (author_id=155601) is Ty Franck (author_id=123977) + Daniel Abraham (10297)
    """
    query = text("""SELECT a.author_id, author_canonical, author_birthplace
        FROM pseudonyms p
        LEFT OUTER JOIN authors a ON p.author_id = a.author_id
        WHERE pseudonym = :pseudonym_id""")
    results = conn.execute(query, pseudonym_id=author_id).fetchall()
    if results:
        return [z['author_birthplace'] for z in results]
    else:
        return [None]


def get_author_country(conn, filter_args, check_pseudonyms=True,
                       overrides=None):
    fltr, params = get_filters_and_params_from_args(filter_args)

    if overrides is True:
        overrides = load_hacks() # TODO: cache this for future calls


    # TODO: support args as a vanilla dict, not just an argparse Namespace
    if overrides and filter_args.exact_author:
        # Try to use the override ASAP - if we don't have an exact name, we'll
        # try again later after we get a name from the database
        try:
            return overrides[filter_args.exact_author]
        except KeyError:
            pass


    query = text("""select author_id, author_canonical, author_birthplace
      from authors a
      where %s""" % fltr)
    results = conn.execute(query, **params).fetchall()

    if not results:
        # logging.error('No author found matching %s' % (filter_args))
        return None
    elif len(results) > 1:
        raise AmbiguousArgumentsError('Multiple (%d) authors matching %s: %s...' %
                                        (len(results), filter_args, results[:5]))
    else:
        rec = results[0]
        if overrides and rec['author_canonical'] in overrides:
            return overrides[ rec['author_canonical'] ]
        birthplace = rec['author_birthplace']
        if not birthplace and check_pseudonyms:
            all_bps = get_birthplaces_for_pseudonym(conn, rec['author_id'])
            bps = [z for z in all_bps if z is not None] # because [None] is True-ish
            if bps:
                return ','.join([get_country(z) for z in bps])
        return get_country(birthplace)



if __name__ == '__main__':
    args = parse_args(sys.argv[1:], description='Report birth country of author',
                      supported_args='a')

    conn = get_connection()
    overrides = load_hacks()
    print(get_author_country(conn, args, overrides=overrides))
