#!/usr/bin/env python3
# TODO: This currently counts hb/tpb/mmpb/ebook/audio/etc editions separately,
#       which is probably not the best.  This filtering/merging should probably
#       be done in the publisher_books module though.


import logging
import pdb
import sys

from common import (get_connection, parse_args, get_filters_and_params_from_args,
                    AmbiguousArgumentsError)

from publisher_books import get_publisher_books
from author_gender import analyse_authors


if __name__ == '__main__':
    # script_name = basename(sys.argv[0])

    args = parse_args(sys.argv[1:],
                      description='Show author gender for books from a publisher',
                      supported_args='kpy')

    conn = get_connection()
    results = get_publisher_books(conn, args,
                                  countries=[z.upper() for z in args.countries])

    analyse_authors(conn, results)
