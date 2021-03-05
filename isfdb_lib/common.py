#!/usr/bin/env python3
"""
Code which is used by pretty much every script, broadly covering:
* Getting a database connection
* Parsing command-line arguments
* Turning the arguments into SQL snippets for filtering results
More specialized library functions should go elsewhere.
"""

from argparse import ArgumentParser
import logging
import os
import pdb
import sys

from sqlalchemy import create_engine
from sqlalchemy.sql import text

from isfdb_lib.expansions import EXPANSION_MAPPINGS

class AmbiguousArgumentsError(Exception):
    pass


def get_connection(connection_string=None):
    # https://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls
    # https://docs.sqlalchemy.org/en/latest/core/engines.html#mysql
    if not connection_string:
        connection_string = os.environ.get('ISFDB_CONNECTION_DETAILS')
    engine = create_engine(connection_string)
    conn = engine.connect()
    return conn


def create_parser(description, supported_args):
    """
    Return an ArgumentParser with support for arguments specified by supported_args.
    supported args is a string or iterable containing letters indicating the
    script supports the following:
    * a : author
    * c : award category (e.g. "Best Novel", "Best Novella")
    * g : tag
    * k : country (2 character codes, e.g. "us", "ca")
    * n : work types (e.g. novel, anthology, chapbook - i.e. title_ttype not pub_ctype)
    * p : publisher
    * t : book title
    * v : verbose mode
    * w : award (e.g. "Hugo Award", "Nebula Award"
    * y : year(s) (e.g. "2001", "1970-2020")

    With the exception of v/verbose and y/year, two argument variants are supported:
    * -x foo : case insensitive pattern match
    * -X "Exact Match" : exact match, but can be passed multiple times for an OR check

    Publisher support also supports a -PP additional argument to use a manually
    maintained (and likely very incomplete) list of publisher aliases.
    """
    parser = ArgumentParser(description=description)

    if supported_args:
        low_args = supported_args.lower()
    else:
        low_args = ''

    # PRESUMPTION: if we support the pattern match form, we also want to support
    #              the exact form
    # TODO: I don't think we need/want the "not supported_args or" test
    # NOTE: anything added here also (probably) needs an implementation in
    #       get_filters_and_params_from_args() - although this may well just be
    #       a case of adding it to param2column_names
    if not supported_args or 'a' in low_args:
        parser.add_argument('-a', nargs='?', dest='author',
                            help='Author to search on (pattern match, case insensitive)')
        parser.add_argument('-A', action='append', dest='exact_author', default=[],
                            help='Author to search on (exact match, case sensitive)')

    if not supported_args or 't' in low_args:
        parser.add_argument('-t', nargs='?', dest='title',
                            help='Title to search on (pattern match, case insensitive)')
        parser.add_argument('-T', action='append', dest='exact_title', default=[],
                            help='Title to search on (exact match, case sensitive)')

    if not supported_args or 'p' in low_args:
        parser.add_argument('-p', nargs='?', dest='publisher',
                            help='Publisher to search on (pattern match, case insensitive)')
        parser.add_argument('-P', action='append', dest='exact_publisher', default=[],
                            help='Publisher to search on (exact match, case sensitive)')
        parser.add_argument('-PP', action='store_true', dest='exact_publisher_expanded',
                            help='Expand known publisher to all known variants (requires -P)')

    if not supported_args or 'n' in low_args:
        parser.add_argument('-n', dest='work_types', action='append', default=[],
                            help='Types of work to search on e.g. novel, chapbook, anthology, etc '
                            '(case insensitive but otherwise exact match, multiple "OR" values allowed)')

    if not supported_args or 'w' in low_args:
        parser.add_argument('-w', nargs='?', dest='award',
                            help='Award to search on (pattern match, case insensitive)')
        parser.add_argument('-W', action='append', dest='exact_award', default=[],
                            help='Award to search on (exact match, case sensitive)')

    # Q: Could we merge n and c args in some cases?  Locus' "Best SF Novel" etc
    # means maybe not though
    if not supported_args or 'c' in low_args:
        # -c is a bit flakey, given that novel is a substring of novella and novellette
        parser.add_argument('-c', nargs='?', dest='award_category',
                            help='Award category to search on (pattern match, case insensitive)')
        parser.add_argument('-C', action='append', dest='exact_award_category', default=[],
                            help='Award category to search on (exact match, case sensitive)')

    if not supported_args or 'y' in low_args:
        parser.add_argument('-y', nargs='?', dest='year',
                            help='Year to search on (publication year for books, '
                            'ceremony year for awards; from-to ranges are acceptable')

    if not supported_args or 'k' in low_args:
        parser.add_argument('-k', dest='countries', action='append', default=[],
                            help='2-character code for country/countries to filter/report on')

    if not supported_args or 'g' in low_args:
        parser.add_argument('-g', nargs='?', dest='tag',
                            help='Tag to search on (pattern match, case insensitive)')
        parser.add_argument('-G', action='append', dest='exact_tag', default=[],
                            help='Tag to search on (exact match, case sensitive)')

    parser.add_argument('-v', action='store_true', dest='verbose',
                        help='Log verbosely')
    return parser


def parse_args(cli_args, description='No description provided',
               supported_args=None, parser=None):
    # parser arg is basically if you want to re-use the same parser multiple
    # times (but with different args) in the same program
    if not parser:
        parser = create_parser(description, supported_args)
    args = parser.parse_args(cli_args)
    return args

# TODO: The callers that rely on this should be updated to pass a dict with
# this in, and then we can make this generic.
# If the value ends in underscore, then it is a prefix rather than a renaming
DEFAULT_COLUMN_MAPPINGS = {
    'year': 'award_'
}

def _generate_prefixed_column_name(column_name, name_mapping):
    # TODO: this should support alternate column names e.g.
    # year => copyright_date
    default_name = DEFAULT_COLUMN_MAPPINGS.get(column_name, '')

    try:
        actual_name = name_mapping[column_name]
        if actual_name.endswith('_'):
            full_name = '%s%s' % (actual_name, column_name)
        else:
            full_name = actual_name
    except KeyError:
        if default_name:
            if default_name.endswith('_'):
                full_name = '%s%s' % (default_name, column_name)
            else:
                full_name = default_name
        else:
            full_name = column_name
    return full_name


def get_filters_and_params_from_args(filter_args, column_name_mappings=None):
    # This theoretically is generic, but the tablename_foo column names
    # make it less so.  (TODO (maybe): have extra prefix arg?)
    # TODO: this should support a bog-standard Python dict, as well as the
    #            output from parse_args()

    if not column_name_mappings:
        column_name_mappings = {}

    filters = []
    params = {}

    arg_dict = filter_args.__dict__ # Q: Is there another way to do []/.get() style access?

    # What the characters in the second tuple element mean:
    # e: exact match
    # g: group exact match
    # p: pattern
    # y: year
    param2column_names = {
        'author': ('author_canonical', 'pe'),
        'title': ('title_title', 'pe'),
        # TODO: award should also support award_type_short_name - primarily for BSFA
        'award': ('award_type_name', 'pe'),
        'award_category': ('award_cat_name', 'pe'),
        'work_types': ('title_ttype', 'g'), # Note prior comment about 'g' not implemented!!!!

        'publisher': ('publisher_name', 'pex'),
        'tag': ('tag_name', 'pe'),

        # 'year': ('%s_year' % (column_name_prefixes.get('year', 'award')), 'y'),
        'year': (_generate_prefixed_column_name('year', column_name_mappings), 'y'),
    }
    # pdb.set_trace()
    for prm, (col, variants) in param2column_names.items():

        val = arg_dict.get(prm)
        # print(prm, val)
        # print(val)
        if not val: # Does this break anything?  Not sure why I didn't do it originally
            # continue
            pass
        if variants in ('pe', 'pex'): # pattern and exact match, optionally expand
            if val is not None:
                # pattern variant
                params[prm] = '%%%s%%' % (val.lower())
                filters.append('LOWER(%s) LIKE :%s' % (col, prm))
                continue

            try:
                # TODO: double check we didn't raise beforehand Q: What does this refer to?
                exact_prm = 'exact_' + prm
                exact_val = arg_dict[exact_prm]
            except KeyError:
                continue # to next argument

            if 'x' in variants and arg_dict[exact_prm + '_expanded']:
                expanded_vals = []
                for v in exact_val:
                    try:
                        exp = EXPANSION_MAPPINGS[prm][v]
                    except KeyError as err:
                        raise KeyError(f'"{v}" is not a known expandable {prm}')
                    expanded_vals.extend(exp)
                    logging.debug(f'Expanded vals for {v} are {expanded_vals}')
                exact_val = expanded_vals


            # PRESUMPTION: "colname = value" is more efficient than
            # "colname IN [value]", so use = over IN when there is a single
            # value for an argument that can take take multiple values
            # hasattr(foo,'extend') is to avoid doing the wrong thing
            # on string values w.r.t. len(foo)  (Ideally this shouldn't ever
            # happen if the arg parser is properly configured.)
            if exact_val is None or \
               (hasattr(exact_val, 'extend') and len(exact_val) == 0):
                continue # ignore it
            if hasattr(exact_val, 'extend'): # Duck type for list
                if len(exact_val) > 1:
                    params[exact_prm] = exact_val
                    filters.append('%s IN :%s' % (col, exact_prm))
                else:
                    params[exact_prm] = exact_val[0]
                    filters.append('%s = :%s' % (col, exact_prm))
            else:
                params[exact_prm] = exact_val
                filters.append('%s = :%s' % (col, exact_prm))
        elif variants == 'g':
            # group (exact) match,
            # i.e. value should match one of the values passed in the group arg
            # e.g. '-n NOVEL -n CHAPBOOK' will match NOVEL *or* CHAPBOOK
            if val is None or len(val) == 0:
                continue
            params[prm] = [z.lower() for z in val]
            filters.append('LOWER(%s) IN :%s' % (col, prm))
        elif variants == 'y': # year
            if val is None:
                continue
            if '-' in val:
                from_year, to_year = val.split('-')
                params['from_year'] = (int(from_year)  if from_year else -1000)
                params['to_year'] = (int(to_year) if to_year else 2999)
                filters.append('YEAR(%s) BETWEEN :from_year AND :to_year' % (col))
            else:
                params[prm] = int(val)
                filters.append('YEAR(%s) = :%s' % (col, prm))

    fltr = ' AND '.join(filters)

    #print(fltr, params)
    #sys.exit(1)
    return fltr, params
