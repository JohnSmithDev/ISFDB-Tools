#!/usr/bin/env python3
"""
Churn through a bunch of publications (either all, or filtered by some criteria)
and report on any that have both ASIN+ISBN defined, but which are inconsistent
with what Fixer has.  (This can happen if an editor has made a submission based
on a non-local Amazon store, but Amazon served them localized content based on
their geo-IP information, amongst other reasons)
"""

from collections import defaultdict, Counter
# from functools import reduce, lru_cache
import logging
import pdb
import sys


from sqlalchemy.sql import text

from common import (get_connection, parse_args, AmbiguousArgumentsError,
                    get_filters_and_params_from_args)

from isfdb_lib.ids_in_memory import load_fixer_ids

LOG_UNKNOWN_ISBNS = False # Can be very noisy due to audiobooks

def report_on_inconsistent_ids(conn, args, isbn_mappings, output_function=print):
    fltr, params = get_filters_and_params_from_args(
        args, column_name_mappings={'year': 'pub_year'})

    # TODO (ideally): restore this: WHERE i.identifier_type_name IN :valid_id_types

    query = text("""SELECT p.pub_id, pub_title, pub_year,
    p.publisher_id, publisher_name,
    pub_ptype, pub_isbn, pub_price,
    i.identifier_id, i.identifier_type_id, it.identifier_type_name, identifier_value
    FROM pubs p
    LEFT OUTER JOIN publishers ON publishers.publisher_id = p.publisher_id
    LEFT OUTER JOIN identifiers i ON i.pub_id = p.pub_id
    LEFT OUTER JOIN identifier_types it ON i.identifier_type_id = it.identifier_type_id
    WHERE it.identifier_type_name IN ('ASIN', 'Audible-ASIN')
      AND p.pub_isbn IS NOT NULL
      AND %s
    ORDER BY publisher_name, p.pub_id, identifier_value;""" % (fltr))

    results = conn.execute(query, **params)
    bad_count = 0
    unknown_isbns = 0
    prev_pub_id = None
    current_rows = []

    def do_checks(rows):
        nonlocal bad_count, unknown_isbns
        # pdb.set_trace()
        # All rows *should* be identical, apart from ASIN-related
        first_row = rows[0]
        pub_id = first_row['pub_id']
        isbn = first_row['pub_isbn']
        asins = {z['identifier_value'] for z in rows}
        try:
            isbn_details = isbn_mappings[isbn]
            fixer_asin = isbn_details[2]
            if fixer_asin and fixer_asin not in asins:
                bad_count += 1
                logging.warning(f'{bad_count}. ASIN mismatch Fixer ASIN {fixer_asin} != '
                                f'ISFDB ASIN(s) {asins} / {first_row}')
        except KeyError:
            if LOG_UNKNOWN_ISBNS:
                logging.warning(f'ISBN {isbn} not found in ISBN mappings?!?  ({i}, {row})')
            unknown_isbns += 1

    for i, row in enumerate(results, 1):
        pub_id = row['pub_id']
        # output_function(row)
        if prev_pub_id is not None and prev_pub_id != pub_id:
            do_checks(current_rows)
            current_rows = []
        prev_pub_id = pub_id
        current_rows.append(row)

    if current_rows:
        do_checks(current_rows)

    output_function(f'# Encountered {unknown_isbns} unknown-to-Fixer ISBNs')

if __name__ == '__main__':
    args = parse_args(sys.argv[1:],
                      description="Report on ISBN/ASIN information that is inconsistent with Fixer",
                      supported_args='y') # TODO: also publisher?

    conn = get_connection()

    isbn_mappings, asin_mappings = load_fixer_ids() # Don't think we need asin_mappings

    report_on_inconsistent_ids(conn, args, isbn_mappings)
