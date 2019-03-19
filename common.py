#!/usr/bin/env python3

from argparse import ArgumentParser
import os
import pdb

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

def parse_args(cli_args, description, supported_args=None):
    parser = ArgumentParser(description=description)

    if supported_args:
        low_args = supported_args.lower()
    else:
        low_args = ''

    # PRESUMPTION: if we support the pattern match form, we also want to support
    #              the exact form
    if not supported_args or 'a' in low_args:
        parser.add_argument('-a', nargs='?', dest='author',
                            help='Author to search on (pattern match, case insensitive)')
        parser.add_argument('-A', nargs='?', dest='exact_author',
                            help='Author to search on (exact match, case sensitive)')

    if not supported_args or 't' in low_args:
        parser.add_argument('-t', nargs='?', dest='title',
                            help='Title to search on (pattern match, case insensitive)')
        parser.add_argument('-T', nargs='?', dest='exact_title',
                            help='Title to search on (exact match, case sensitive)')

    if not supported_args or 'w' in low_args:
        parser.add_argument('-w', nargs='?', dest='award',
                            help='Award to search on (pattern match, case insensitive)')
        parser.add_argument('-W', nargs='?', dest='exact_award',
                            help='Award to search on (exact match, case sensitive)')
    if not supported_args or 'c' in low_args:
        # -c is a bit flakey, given that novel is a substring of novella and novellette
        parser.add_argument('-c', nargs='?', dest='award_category',
                            help='Award category to search on (pattern match, case insensitive)')
        parser.add_argument('-C', nargs='?', dest='exact_award_category',
                            help='Award category to search on (exact match, case sensitive)')

    if not supported_args or 'y' in low_args:
        parser.add_argument('-y', nargs='?', dest='year', type=int,
                            help='Year to search on (publication year for books, '
                            'ceremony year for awards)')

    args = parser.parse_args(cli_args)
    return args

def get_filters_and_params_from_args(filter_args):
    # This theoretically is generic, but the tablename_foo column names
    # make it less so.  (TODO (maybe): have extra prefix arg?)

    filters = []
    params = {}
    # pdb.set_trace()


    arg_dict = filter_args.__dict__ # Q: Is there another way to do []/.get() style access?

    param2column_names = {
        'author': ('author_canonical', 'pe'),
        #'exact_author': 'author_canonical',

        'title': ('title_title', 'pe'),
        #'exact_title': 'title_title',

        'award': ('award_type_name', 'pe'),
        #'exact_award': 'award_type_name',

        'award_category': ('award_cat_name', 'pe'),
        #'exact_award_category': 'award_cat_name',

        'year': ('award_year', 'y'),
        #'exact_author': 'author_canonical'
    }
    # pdb.set_trace()
    for prm, (col, variants) in param2column_names.items():

        val = arg_dict.get(prm)
        if variants == 'pe': # pattern and exact match
            try:
                if val is not None:
                    # pattern variant
                    params[prm] = '%%%s%%' % (val.lower())
                    filters.append('lower(%s) like :%s' % (col, prm))

                # TODO: double check we didn't raise beforehand
                exact_prm = 'exact_' + prm
                exact_val = arg_dict[exact_prm]
                if exact_val is not None:
                    params[exact_prm] = exact_val
                    filters.append('%s = :%s' % (col, exact_prm))
            except KeyError:
                pass
        elif variants == 'y': # year
            if val is None:
                continue
            params[prm] = val
            filters.append('YEAR(%s) = :%s' % (col, prm))


    OLD_STYLE = """
    if filter_args.author:
        filters.append('lower(author_canonical) like :author')
        params['author'] = '%%%s%%' % (filter_args.author.lower())
    if filter_args.exact_author:
        filters.append('author_canonical = :exact_author')
        params['exact_author'] = filter_args.exact_author
    if filter_args.title:
        filters.append('lower(title_title) like :title')
        params['title'] = '%%%s%%' % (filter_args.title.lower())
    if filter_args.exact_title:
        filters.append('title_title = :exact_title')
        params['exact_title'] = filter_args.exact_title

    if filter_args.award:
        filters.append('lower(award_type_name) like :award')
        params['award'] = '%%%s%%' % (filter_args.award.lower())
    if filter_args.exact_award:
        filters.append('award_type_name = :exact_award')
        params['exact_award'] = filter_args.exact_award
    if filter_args.award_category:
        filters.append('lower(award_cat_name) like :award_category')
        params['award'] = '%%%s%%' % (filter_args.award_category.lower())
    if filter_args.exact_award_category:
        filters.append('award_cat_name = :exact_award_category')
        params['exact_award_category'] = filter_args.exact_award_category
    """

    filter = ' AND '.join(filters)

    return filter, params
