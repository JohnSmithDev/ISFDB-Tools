#!/usr/bin/env python3

from argparse import ArgumentParser
import os
import pdb
import sys

from sqlalchemy import create_engine
from sqlalchemy.sql import text

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

    if not supported_args or 'n' in low_args:
        parser.add_argument('-n', dest='work_types', action='append', default=[],
                            help='Types of work to search on e.g. novels, novellas, etc '
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


def get_filters_and_params_from_args(filter_args, column_name_prefixes=None):
    # This theoretically is generic, but the tablename_foo column names
    # make it less so.  (TODO (maybe): have extra prefix arg?)
    # TODO: this should support a bog-standard Python dict, as well as the
    #            output from parse_args()

    if not column_name_prefixes:
        column_name_prefixes = {}

    filters = []
    params = {}

    arg_dict = filter_args.__dict__ # Q: Is there another way to do []/.get() style access?

    # What the characters in the second tuple element mean:
    # e: exact match
    # g: group exact match (I think this has never been implemented, and 'e'
    #    allows groups/multiple values to work) TODO: verify and remove if tre
    # p: pattern
    # y: year
    param2column_names = {
        'author': ('author_canonical', 'pe'),
        'title': ('title_title', 'pe'),
        # TODO: award should also support award_type_short_name - primarily for BSFA
        'award': ('award_type_name', 'pe'),
        'award_category': ('award_cat_name', 'pe'),
        'work_types': ('title_ttype', 'g'), # Note prior comment about not implemented!!!!

        'publisher': ('publisher_name', 'pe'),
        'tag': ('tag_name', 'pe'),
        'year': ('%s_year' % (column_name_prefixes.get('year', 'award')), 'y'),
    }
    # pdb.set_trace()
    for prm, (col, variants) in param2column_names.items():

        val = arg_dict.get(prm)
        # print(prm, val)
        # print(val)
        if not val: # Does this break anything?  Not sure why I didn't do it originally
            # continue
            pass
        if variants == 'pe': # pattern and exact match
            try:
                if val is not None:
                   # pattern variant
                    params[prm] = '%%%s%%' % (val.lower())
                    filters.append('LOWER(%s) LIKE :%s' % (col, prm))

                # TODO: double check we didn't raise beforehand
                exact_prm = 'exact_' + prm
                exact_val = arg_dict[exact_prm]
                # PRESUMPTION: "colname = value" is more efficient than
                # "colname IN [value]", so use = over IN when there is a single
                # value for an argument that can take take multiple values
                # hasattr(foo,'extend') is to avoid doing the wrong thing
                # on string values w.r.t. len(foo)  (Ideally this shouldn't ever
                # happen if the arg parser is properly configured.)
                if exact_val is None or \
                   (hasattr(exact_val, 'extend') and len(exact_val) == 0):
                    continue # ignore it
                if hasattr(exact_val, 'extend'):
                    if len(exact_val) > 1:
                        params[exact_prm] = exact_val
                        filters.append('%s IN :%s' % (col, exact_prm))
                    else:
                        params[exact_prm] = exact_val[0]
                        filters.append('%s = :%s' % (col, exact_prm))
                else:
                    params[exact_prm] = exact_val
                    filters.append('%s = :%s' % (col, exact_prm))
            except KeyError:
                pass
        elif variants == 'g': # group (exact) match
            pass # TODO
            # params[prm] = [z.lower() for z in val]
            # filters.append('LOWER(%s) IN :%s' % (col, prm))
        elif variants == 'y': # year
            if val is None:
                continue
            if '-' in val:
                from_year, to_year = val.split('-')
                params['from_year'] = int(from_year)
                params['to_year'] = int(to_year)
                filters.append('YEAR(%s) BETWEEN :from_year AND :to_year' % (col))
            else:
                params[prm] = int(val)
                filters.append('YEAR(%s) = :%s' % (col, prm))

    fltr = ' AND '.join(filters)

    #print(fltr, params)
    #sys.exit(1)
    return fltr, params
