#!/usr/bin/env python3
"""
An experiment into whether you can store all the ASINs and ISBNs in memory,
and how fast you can query them using basic Python data structures.  It can
be optionally used with the id_checker.py Flask webserver to:

(a) Avoid making repeated calls to the database, at the expense of slower startup
    and increased memory usage
(b) Provide increased functionality, some/most of which could be backported to
    the "original" version/functionality of id_checker.py

UPDATE: Now has code to use the exported ISBN and ASIN data from Fixer
(see email 2020-04-02 from Ahasuerus)

Stats as of end March 2020:

- 50496 unique ISBNs and ASINs
- Loads from database in just under 2 seconds (could be improved with pickle)
- Takes up 16GB stroring as strings; ISBN-13s coule be 64-bit ints for better
  storage and (probably) perf
- Querying 1 million random 978+{10 digits} IDs takes around 0.6 seconds, with
  a typical hit rate of around 25-30 known IDs.  NB: This is/was for the base
  functionality, excluding the Fixer-related stuff, which slows things down a
  bit.

UPDATE#2: Format has changed again per
http://www.isfdb.org/wiki/index.php/User:Fixer/Queues#Lists_of_ISBNs_and_ASINs_known_to_Fixer


"""

from collections import defaultdict
from datetime import datetime
import logging
import os
import pdb
import sys
import time

from sqlalchemy.sql import text

from common import get_connection
from isbn_functions import isbn10and13
from isfdb_lib.identifier_related import check_asin, check_isbn

FIXER_DUMP_DIR = os.environ.get('ISFDB_FIXER_DUMP_DIR') or \
                 os.path.join('/', 'mnt', 'data2019', '_isfdb_')


# These only get populated when initialise() is called
all_isfdb_ids = {}
isbn_mappings = {}
asin_mappings = {}


MAX_UNKNOWNS_TO_LOG = 10 # was 3, but this doesn't help debugging


# TODO: make this an Enum?
# I think these codes are for the pre July 2020 files; the newer files have
# codes with different meanings?
FIXER_STATUS_CODES = ['Not processed', # 0
                      'In ISFDB', # 1
                      'Submitted', # 2
                      'Suspended', # 3
                      'Rejected' # 4
                      ]
# As of Sep 2020, there's also a priority/queue "n" for new, as yet unprioritized
# IDs
NEW_FIXER_STATUS_CODES = ['Insufficient information', # 0
                          'High priority', # 1 : major publisher/established author
                          'Medium priority', # 2 : self pub/minor author already known
                          'Low priority', # 3 : unknown self-pub author
                          'Already uploaded', # 4
                          'Pending upload', # 5
                          'Unused #6',
                          'Unused #7',
                          'Submitted to server', #8
                          'Manually rejected' #9
                          ]


DB_QUERIES = [('ASIN',"""SELECT DISTINCT identifier_value v
    FROM identifiers i
    LEFT OUTER JOIN identifier_types it ON i.identifier_type_id = it.identifier_type_id
    WHERE it.identifier_type_name IN ('ASIN', 'Audible-ASIN');"""),
              ('ISBN', """SELECT DISTINCT pub_isbn v FROM pubs
                    WHERE pub_isbn IS NOT NULL;"""),
              ('AudibleUK-ASIN', """SELECT asin v FROM
                  (SELECT SUBSTRING_INDEX(url, '/', -1) asin
                   FROM webpages
                   WHERE url LIKE '%www.audible%' AND pub_id IS NOT NULL) foo
                 WHERE asin LIKE 'B%';""")]

def load_ids(conn, output_function=print):
    all_isfdb_ids = set()
    start = time.time()
    output_function('Loading ASINs and ISBNs into memory...')
    for i, (label, query) in enumerate(DB_QUERIES, 1):
        results = conn.execute(text(query)).fetchall()
        all_isfdb_ids.update([z['v'] for z in results])
        output_function('%d/%s. Loaded %d cumulative IDs in %.3f seconds, size=%.1fMB' %
                        (i, label, len(all_isfdb_ids), time.time() - start,
                         sys.getsizeof(all_isfdb_ids) / (1024 * 1024)))
    return all_isfdb_ids

def load_fixer_ids(output_function=print):
    """
    Returns a tuple of:
    * A dict mapping ISBNs Fixer knows about to a tuple of
      - their status in Fixer,
      - their priority in Fixer (if status==0), else None
      - their ASIN (if any)
    * A dict mapping ASINs to ISBNs or None - the latter if the publication
      doesn't have an ISBN
    """

    isbn_mappings = {}

    start = time.time()
    for line in open(os.path.join(FIXER_DUMP_DIR, 'AllISBNs.txt')):
        if line.endswith('\n'):
            line = line[:-1]
        bits = line.split('|')
        asin = None
        if len(bits) == 3:
            # Older format (early 2020)
            isbn, raw_status, raw_priority = bits
        elif len(bits) == 2:
            # Short-lived format (July-Sep 2020)
            # I don't *think* we ever did anything useful with the status, so
            # no big deal faking it.
            isbn, raw_priority = bits
            raw_status = 0
        else:
            # Newest format as of Sep 2020
            raw_status = 0
            isbn10, isbn, raw_priority, asin = bits
        try:
            priority = int(raw_priority)
        except ValueError:
            if raw_priority in ('', None):
                priority = None
            else:
                priority = raw_priority # e.g. 'n'
        isbn_mappings[isbn] = (int(raw_status), priority, asin)

    output_function('Loaded %d Fixer ISBNs in %.3f seconds, size=%.1fMB' %
                    (len(isbn_mappings), time.time() - start,
                     sys.getsizeof(isbn_mappings) / (1024 * 1024)))


    asin_mappings = {}

    start = time.time()
    for line in open(os.path.join(FIXER_DUMP_DIR, 'AllASINs.txt')):
        if line.endswith('\n'):
            line = line[:-1]
        bits = line.split('|')
        if len(bits) == 2:
            # Older format (early 2020)
            asin, isbn = bits
        else:
            if len(bits[2]) >= 10:
                # Short-lived format (July-Sep 2020),
                #   Middle field is a 0 or 1 boolean "disposition flag" indicating
                #   whether submitted or not.  For now, we don't care about it
                asin, _, isbn = bits
            else:
                # Even newer format (Sep 2020 onwards), final value is a queue/
                # priority that we don't care about
                asin, isbn, _ = bits
        asin_mappings[asin] = isbn or None

    output_function('Loaded %d Fixer ASINs in %.3f seconds, size=%.1fMB' %
                    (len(asin_mappings), time.time() - start,
                     sys.getsizeof(asin_mappings) / (1024 * 1024)))


    return isbn_mappings, asin_mappings

def possible_asin_but_not_isbn(val):
    # TODO (probably): Also check it's 10 chars?
    return not ( 48 <= ord(val[0]) <= 57 ) # faster than re.match on \D ?


def batch_check_in_memory(list_of_ids, do_fixer_checks=True,
                check_both_isbn10_and_13=True):
    """
    Given a list/iterable of IDs, return a list of {"id": whatever, "known": bool}.
    Returned list is not guaranteed to be in the same order as input argument,
    although it probably will be.

    EDIT: the dicts/objects in the response now have additional keys/values,
    these will be separately documented.

    Doing fixer checks multiplies the time taken for a batch roughly threefold.
    """

    ret = []
    for val in list_of_ids:
        if check_both_isbn10_and_13 and not possible_asin_but_not_isbn(val):
            both_isbns = isbn10and13(val)
            matches = [val for val in both_isbns if val in all_isfdb_ids]
            if any(matches): # Remember: [False, False] evaluates to True
                known = True
                # First match could be the ISBN variant we didn't supply if
                # ISFDB has both ISBN-10 and ISBN-13,  but no big deal?
                matched_id = [z for z in matches if z][0]
            else:
                known = False
        else:
            known = val in all_isfdb_ids
            matched_id = val
        info = {'id': val, 'supplied_id': val, 'known': known}
        if known:
            info['matched_id'] =  matched_id
        # pdb.set_trace()
        if not known and do_fixer_checks:
            if possible_asin_but_not_isbn(val):
                # Try to convert ASIN to ISBN
                try:
                    fixer_isbn = asin_mappings[val]
                    info['asin_known_to_fixer'] = True
                    #  if fixer_isbn: TODO...

                except KeyError:
                    info['asin_known_to_fixer'] = False
            try:
                info['status'], info['priority'], _ = isbn_mappings[val]
            except KeyError:
                pass
        ret.append(info)
    return ret


def batch_check_with_stats(vals, do_fixer_checks=True, check_both_isbn10_and_13=True,
                output_function=print, label=''):
    """
    Wrapper function for batch_check_in_memory() with extra logging, possibly
    only of interest in standalone script contexts?
    """

    start = time.time()
    results = batch_check_in_memory(vals, do_fixer_checks, check_both_isbn10_and_13)
    duration = time.time() - start
    unknowns = []
    status_counts = defaultdict(int)
    for item in results:
        if not item['known']:
            unknowns.append(item['supplied_id'])
            # Record any Fixer status
            try:
                status_counts[item['status']] += 1
            except KeyError:
                pass
    output_function('Checked %d %s IDs in %.3f seconds' % (len(vals), label, duration))
    if unknowns:
        unknown_str = '(%s ...)' % (', '.join(unknowns[:MAX_UNKNOWNS_TO_LOG]))
    else:
        unknown_str = ''
    output_function('%d were not known to ISFDB %s' % (len(unknowns), unknown_str))
    if do_fixer_checks and unknowns:
        if status_counts:
            output_function('Of the umknowns, the following are known to Fixer:')
            for k, c in sorted(status_counts.items()):
                if k == 'n':
                    status = 'New/unprioritized'
                else:
                    status = NEW_FIXER_STATUS_CODES[k]
                output_function('* Status "%s" (%s) : %d' % (status, k, c))
        else:
            output_function('None of the unknowns were known to Fixer')
    return results

def batch_stats_pedantic(vals, do_fixer_checks, check_both_isbn10_and_13,
                         output_function=print, label=''):
    return batch_check_with_stats(vals, do_fixer_checks, check_both_isbn10_and_13,
                       output_function, label)


def initialise(conn):
    global all_isfdb_ids, isbn_mappings, asin_mappings
    all_isfdb_ids = load_ids(conn)
    isbn_mappings, asin_mappings = load_fixer_ids()


if __name__ == '__main__':

    if len(sys.argv) > 1:
        num_vals = int(sys.argv[1])
    else:
        # Hit rate on random IDs is about 1/50k, so 1000000 should give 20ish
        # On my box this takes around 0.6 seconds
        num_vals = 1000000

    conn = get_connection()

    initialise(conn)
    print()

    # Some useful test ISBNs that are known to either ISFDB or Fixer, the latter
    # with various statuses and priorities
    batch_stats_pedantic(['B073NXRMWJ', # Kindle edition of A Very British History
                          #'9781640637344', '1110000001005', '9781975353636',
                          #'9789963536504', '9789123671182',

    ],
                         do_fixer_checks=True, check_both_isbn10_and_13=True)

    print()

    from random import randint
    vals = [str(randint(9780000000000, 9789999999999)) for z in range(num_vals)]
    batch_stats_pedantic(vals, do_fixer_checks=True, check_both_isbn10_and_13=True,
                label='randomly generated')

    print()

    fixer_asins = asin_mappings.keys()
    asin_results = batch_stats_pedantic(fixer_asins, do_fixer_checks=False,
                               check_both_isbn10_and_13=False,
                               label="ASINs from Fixer's ASINs")

    print()

    fixer_isbn_for_asins = [z for z in asin_mappings.values() if z]
    isbn_from_asin_results = batch_stats_pedantic(fixer_isbn_for_asins, do_fixer_checks=False,
                                         check_both_isbn10_and_13=True,
                                         label="ISBNs mapped from Fixer's ASINs")

    # pdb.set_trace()



