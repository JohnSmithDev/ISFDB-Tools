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
from gender_analysis import (analyse_authors_by_gender, report_gender_analysis,
                             year_data_as_cells)


if __name__ == '__main__':
    # script_name = basename(sys.argv[0])

    args = parse_args(sys.argv[1:],
                      description='Show author gender for books from a publisher',
                      supported_args='kpy')

    conn = get_connection()
    results = get_publisher_books(conn, args,
                                  countries=[z.upper() for z in args.countries])

    stats = analyse_authors_by_gender(conn, results)
    report_gender_analysis(*stats)

    year_data = year_data_as_cells(stats[2], output_function=print)
    # for row in year_data:
    #    print(','.join([str(z) for z in row]))
