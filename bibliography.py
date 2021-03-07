#!/usr/bin/env python3
"""
Output an author's bibliography, similar to
http://www.isfdb.org/cgi-bin/ch.cgi?503

Known bugs/issues:
* Requires exact author name to be specified (although it can be any known
  alias/variant)
* Doesn't distinguish between pseudonyms
* Currently only outputs novels
* Doesn't indicate collaborations
* Hardcoded for English language editions only
* Some issues with variant editions e.g. Peter F. Hamilton, Charles Stross
"""

from collections import defaultdict, Counter, namedtuple
from datetime import date
from functools import reduce, lru_cache
from itertools import chain
import logging
import pdb
import sys


from sqlalchemy.sql import text

from common import (get_connection, create_parser, parse_args,
                    AmbiguousArgumentsError)
from isfdb_utils import (convert_dateish_to_date, merge_similar_titles)
from author_aliases import get_author_alias_ids
from deduplicate import (DuplicatedOrMergedRecordError,
                         make_list_excluding_duplicates)
from publisher_variants import REVERSE_PUBLISHER_VARIANTS

# See language table, titles.title_language
VALID_LANGUAGE_IDS = [17]

DEFAULT_TITLE_TYPES = ['NOVEL']
#DEFAULT_TITLE_TYPES = ['NOVEL', 'CHAPBOOK']
# DEFAULT_TITLE_TYPES = ['SHORTFICTION']

# Not sure if (a) I need these, and (b) how they're converted to Python dates
# DATES_TO_EXCLUDE = {date(0,1,1), date(8888, 1, 1)}
DATES_TO_EXCLUDE = set()

def safe_limit(values, func, values_to_exclude=None):
    if not values_to_exclude:
        values_to_exclude = []
    valid_values = [z for z in values if z is not None and z not in values_to_exclude]
    if not valid_values:
        return None
    else:
        return func(valid_values)

def safe_min(values, values_to_exclude=None):
    return safe_limit(values, min, values_to_exclude)

def safe_max(values, values_to_exclude=None):
    return safe_limit(values, max, values_to_exclude)



class DuplicateBookError(DuplicatedOrMergedRecordError):
    pass

# This probably needs more work - there's a difference between unknown (0000)
# and never published (8888)
FALLBACK_YEAR = 8888

# TODO: these should be automatically inferred from author's history
MIN_PUB_YEAR = 1990
MAX_PUB_YEAR = 2021

PubStuff = namedtuple('PubStuff', 'pub_id, date, format price')

class BookByAuthor(object):
    """
    Mainly a data class for all the books (and maybe other titles/pubs?) by an
    author, but with some useful helper properties.
    """
    # _tid_to_bba maps title_ids to BookByAuthor, and is used to merge duplicates
    # (as determined by common title_id)
    _tid_to_bba = {}

    @classmethod
    def reset_duplicate_cache(cls):
        """
        If you are processing multiple bibliographies, possibly for the same
        or related author (e.g. variant, maybe co-author too), you need to clear
        out the cache, otherwise later queries for bibliographies will return
        zero or reduced rows.
        """
        cls._tid_to_bba = {}

    def __init__(self, row, author='Author', allow_duplicates=False):
        # Q: I don't see that allow_duplicates is ever used?
        self.title_id = row['title_id']
        self.parent_id = row['title_parent']
        self.title_title = row['title_title'] # Use the .title property over this
        self.title_ttype = row['title_ttype']

        self.copyright_date = convert_dateish_to_date(row['t_copyright'])
        self._copyright_dates = [self.copyright_date]

        self.pub_id = row['pub_id']
        self.pub_title = row['pub_title']
        self.publication_date = convert_dateish_to_date(row['p_publication_date'])
        self._publication_dates = [self.publication_date]
        self.isbns = [row['pub_isbn']]

        pn = row['publisher_name']
        sanitised_publisher = REVERSE_PUBLISHER_VARIANTS.get(pn, pn)
        self.publishers = {sanitised_publisher}

        # Q: should this count twice if title and pub_title are the same?
        valid_titles = [z for z in [self.title_title, self.pub_title] if z]
        self._titles = Counter(valid_titles)

        self.author = author


        self.pub_stuff = PubStuff(self.publication_date, self.publication_date,
                                  row['pub_ptype'], row['pub_price'])
        self.all_pub_stuff = [self.pub_stuff]


        key = self.parent_id or self.title_id
        # self._title_id_to_titles[key].update([self.title, self.pub_title])
        # self._publication_dict[key].update([self.copyright_date, self.publication_date])

        try:
            other = self._tid_to_bba[key]
            other.merge_in_fields(self)
            raise DuplicateBookError('%s (id=%d) already known as %s (id=%d)' %
                                     (self.title, self.title_id,
                                      other.title, other.title_id))

        except KeyError:
            self._tid_to_bba[key] = self


    def merge_in_fields(self, other):
        self._titles.update(other._titles)
        self._copyright_dates.extend(other._copyright_dates)
        self._publication_dates.extend(other._publication_dates)
        self.isbns.extend(other.isbns)
        self.publishers.update(other.publishers)
        self.all_pub_stuff.extend(other.all_pub_stuff)

    @property
    def earliest_copyright_date(self):
        return safe_min(self._copyright_dates, DATES_TO_EXCLUDE)

    @property
    def earliest_publication_date(self):
        return safe_min(self._publication_dates, DATES_TO_EXCLUDE)

    @property
    def latest_publication_date(self):
        return safe_max(self._publication_dates, DATES_TO_EXCLUDE)

    @property
    def prioritized_titles(self):
        return [z[0] for z in self._titles.most_common()]

    @property
    def all_titles(self):
        # This is reasonable for novels, but will be wrong for (most) short fiction,
        # as it will dump out the story name alongside the mag/anth/coll it appears
        # in
        return ' aka '.join(self.prioritized_titles)

    def titles(self, max_length=100):
        # The repeated string concatenation is a bit naive (as opposed to just
        # keeping a running total, and only joining at the end), but in the
        # overall scheme of things, I don't think it matters
        pts = self.prioritized_titles
        ret = pts[0]
        if len(ret) >= max_length:
            ret = ret[:max_length-3] + '...'
            return ret
        for i in range(1, len(pts)):
            try_this = f'{ret} aka {pts[i]}'
            if len(try_this) > max_length:
                return ret
            ret = try_this
        return ret

    @property
    @lru_cache()
    def title(self):
        return self.prioritized_titles[0]

    @property
    @lru_cache()
    def year(self):
        dt = safe_min([self.earliest_copyright_date, self.earliest_publication_date])
        if not dt:
            return FALLBACK_YEAR
        else:
            return dt.year

    def pub_stuff_string(self, min_year=MIN_PUB_YEAR, max_year=MAX_PUB_YEAR):
        with_dates = [z for z in self.all_pub_stuff
                      if z.date and 1800 <= z.date.year <= 2100]
        date_sorted = sorted(with_dates, key=lambda z: z.date)
        year_to_stuff = {} # deliberately not using defaultdict
        for year in range(min_year, max_year+1):
            year_to_stuff[year] = []
            # TODO: make this more efficient
            for stuff in date_sorted:
                if stuff.date.year == year:
                    year_to_stuff[year].append(stuff)
        counts = [len(v) for k, v in sorted(year_to_stuff.items())]

        def num_rep(v):
            if v >= 10:
                return 'X'
            elif v == 0:
                return '.'
            else:
                return str(v)
        return ''.join([num_rep(z) for z in counts])

    def __repr__(self):
        return '%s [%d]' % (self.title, self.year)


def get_raw_bibliography(conn, author_ids, author_name, title_types=DEFAULT_TITLE_TYPES):
    """
    Pulled out of get_bibliography() when testing where a bug was occurring;
    probably not amazingly useful without the post-processing, but it's here
    if you want it...
    """
    # title_copyright is not reliably populated, hence the joining to pubs
    # for their date as well.
    # Or is that just an artefact of 0 day-of-month causing them to be output as None?

    # NB: title_types and pub_ctypes are not the same, the following is a hack
    #     that may not be desirable in some contexts e.g. should OMNIBUS be added
    #     when we want NOVELs?
    # Q: Why do we need to check both title_ttype and pub_ctype?  Isn't the
    #    first enough?

    # logging.debug(f'title_types={title_types}')
    if not title_types:
        title_types = DEFAULT_TITLE_TYPES

    pub_types = set()
    for tt in title_types:
        if tt == 'SHORTFICTION':
            # OMNIBUS also?
            pub_types.update(['COLLECTION', 'CHAPBOOK', 'ANTHOLOGY', 'MAGAZINE'])
        else:
            # Assume user knew what they were doing
            pub_types.update([tt])


    query = text("""SELECT t.title_id, t.title_parent, t.title_title,
          CAST(t.title_copyright AS CHAR) t_copyright,
          t.series_id, t.title_seriesnum, t.title_seriesnum_2,
          t.title_ttype,
          p.pub_id, p.pub_title, CAST(p.pub_year as CHAR) p_publication_date,
          p.pub_isbn, p.pub_price, p.pub_ptype,
          p.publisher_id, pl.publisher_name
    FROM canonical_author ca
    LEFT OUTER JOIN titles t ON ca.title_id = t.title_id
    LEFT OUTER JOIN pub_content pc ON t.title_id = pc.title_id
    LEFT OUTER JOIN pubs p ON pc.pub_id = p.pub_id
    LEFT OUTER JOIN publishers pl ON p.publisher_id = pl.publisher_id
    WHERE author_id IN :author_ids
      AND t.title_ttype IN :title_types
      AND p.pub_ctype IN :pub_types
      AND title_language IN :title_languages
    ORDER BY t.title_id, p.pub_year; """)
    rows = conn.execute(query, {'author_ids':author_ids,
                                'title_types': title_types,
                                'pub_types': list(pub_types), # Doesn't seem to like set?
                                'title_languages': VALID_LANGUAGE_IDS})
    # print(len(rows)) # This only works if you do a .fetchall() above
    return rows


def get_bibliography(conn, author_ids, author_name, title_types=DEFAULT_TITLE_TYPES):
    """
    Given a list of author_ids, return a sorted bibliography.

    author_name is a bit of a hack to avoid having to do another lookup on
    the authors table (which *might* have complications with multiple matches
    e.g. an author with variant names, that a book has been issued under both
    variants?)
    """
    rows = get_raw_bibliography(conn, author_ids, author_name, title_types)

    BookByAuthor.reset_duplicate_cache()

    def make_bba(stuff, allow_duplicates):
        """
        Curried wrapper to BookByAuthor class.
        The use of author_names[0] is a bit of a hack - TODO: better
        """
        bba =  BookByAuthor(stuff, author=author_name,
                            allow_duplicates=allow_duplicates)
        # if bba.year is None or bba.year == FALLBACK_YEAR:
        #    logging.warning('Year is None or %s for %s (possibly unpublished?' %
        #                    (FALLBACK_YEAR, bba))
        return bba

    books = make_list_excluding_duplicates(
        rows, make_bba,
        allow_duplicates=False, duplication_exception=DuplicateBookError)

    if not books:
        # Hack for 1975 Campbell New Writer winner P. J. Plauger, who seems to only
        # have 2 novels, both of which only ever printed as magazine serializations?
        logging.warning('No books found for %s/%s' % (author_ids, author_name))
        return []
    # rows.close() # Doesn't fix the re-run failure
    return sorted(books, key=lambda z: z.year)



def postprocess_bibliography(raw_rows):
    # THIS SEEMS TO BE NO LONGER USED???
    title_id_to_titles = defaultdict(set)
    publication_dict = defaultdict(set)
    # TODO: might be nice to order the titles by most popular first?
    # TODO: better to call merge_similar_titles() here?
    for row in raw_rows:
        key = row['title_parent'] or row['title_id']
        title_id_to_titles[key].update([row['title_title'], row['pub_title']])
        publication_dict[key].update([convert_dateish_to_date(row['t_copyright']),
                                   convert_dateish_to_date(row['p_publication_date'])])

    titles_to_first_pub = {}
    for tid, titles in title_id_to_titles.items():
        pubdates = [z for z in publication_dict[tid] if z is not None]
        titles_to_first_pub[tuple(titles)] = min(pubdates)
    return sorted(titles_to_first_pub.items(), key=lambda z: z[1])


def output_publisher_stats(publisher_counts, output_function=print):
    output_function(f'\n= This author has been published by the following =')
    for i, (publisher, book_count) in enumerate(publisher_counts.most_common()):
        pc = 100 * book_count / len(bibliography)
        if pc < 5 or i > 10:
            output_function('...and %d other publishers' % (len(publisher_counts) - i))
            break
        output_function('%-40s : %3d (%d%%)' % (publisher, book_count, pc))


def get_author_bibliography(conn, author_names, title_types=None):
    # author_ids = get_author_alias_ids(conn, author_names)
    author_name = author_names[0]
    author_ids = get_author_alias_ids(conn, author_name)
    if not author_ids:
        raise AmbiguousArgumentsError('Do not know author "%s"' % (author_names))
    # print(author_ids)
    bibliography = get_bibliography(conn, author_ids, author_name, title_types)
    return bibliography


if __name__ == '__main__':
    parser = create_parser(description="List an author's bibliography",
                      supported_args='anv')
    parser.add_argument('-p', dest='show_publishers', action='store_true',
                        help='Show stats on which publishers this author had')
    args = parse_args(sys.argv[1:], parser=parser)


    conn = get_connection()

    bibliography = get_author_bibliography(conn, args.exact_author, args.work_types)
    publisher_counts = Counter()
    min_year, max_year = 7777, -7777
    pub_dates = [z._publication_dates for z in bibliography]
    flattened_pub_dates = chain(*pub_dates)
    pub_years = [z.year for z in flattened_pub_dates if z and z.year and z.year not in (0, 8888)]
    if pub_years:
        min_year = min(pub_years)
        max_year = max(pub_years)
    if max_year - min_year > 80:
        min_year = MIN_PUB_YEAR
        max_year = MAX_PUB_YEAR

    year_bits = []
    for year in range(min_year, max_year+1):
        year_string = str(year)
        digit = year % 10
        year_chars = {0: '\u2193', # https://unicode-table.com/en/sets/arrow-symbols/#down-arrows
                      1: year_string[0],
                      2: year_string[1],
                      3: year_string[2],
                      4: '0'}
        year_bits.append(year_chars.get(digit, '-'))
    while 1 <= digit <= 3:
        digit += 1
        year_bits.append(year_chars.get(digit, '-'))

    print('     ' + ''.join(year_bits))

    for i, bk in enumerate(bibliography, 1):
        if len(args.work_types) > 1:
            year_bit = f'{bk.title_ttype.lower()}, {bk.year}'
        else:
            year_bit = f'{bk.year}'
        print('%3d. %s %s [%s]' % (i, bk.pub_stuff_string(min_year, max_year),
                                   bk.titles(), year_bit))
        publisher_counts.update(bk.publishers)

    if args.show_publishers:
        output_publisher_stats(publisher_counts)
