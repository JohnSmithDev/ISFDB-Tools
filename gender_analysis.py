#!/usr/bin/env python3
"""
Produce reports/aggregated data based on a list of book-like objects
"""

from collections import Counter, namedtuple
import logging
import pdb

from common import AmbiguousArgumentsError
# from author_aliases import get_definitive_authors
from author_gender import (get_author_gender_cached,
                           get_author_gender_from_ids_and_then_name_cached,
                           UnableToDeriveGenderError)
from award_related import extract_authors_from_author_field
from title_related import get_authors_for_title, get_definitive_authors

GenderStats = namedtuple('GenderStats',
                         'by_gender, by_gender_and_source, '
                         'by_property_gender_and_source, by_books_authors')

GenderType = namedtuple('GenderType', 'heading, key')


def analyse_authors_by_gender(conn, books, output_function=print,
                              prefix_property='year'):
    """
    Given a list of objects that have an author or title_id property,
    return some aggregated stats about them,
    namely a (named)tuple comprising four Counter objects:
    * By gender - key values are M, F, X, H or unknown
    * By gender and source -  key values are (gender-char, source-string) tuples.
      Note that unknowns are excluded from this (as they don't have a source)
    * By prefix_property (typically year), gender and source - key values
      are (property-value, gender-char, source-string).  Unknowns are included
      here, in which case their key will just be (property-value, 'unknown')
    * By gender - but counting authors rather than books
    """

    gender_appearance_counts = Counter()
    gender_source_appearance_counts = Counter()
    year_gender_source_appearance_counts = Counter()
    author_gender = {}
    ignored = [] # TODO: Remove as we don't use it that I can see now?
    for book in books:
        author_bits = get_definitive_authors(conn, book)
        # print(author_bits)

        # Use those <<<<<<<<<<<<<<<<<<<< THIS COMMENT MAKES NO SENSE IN THIS CONTEXT?!?!?
        # else do it via the name
        # TODO (nice to have): do both when possible, and report discrepancies
        # Example: "PJ Manney" for PKD award isn't recognized due to "P. J. " in
        # their author record
        for author in author_bits:
            g_s = None
            if author.id:
                name = author.name
                # Try the author_id...
                try:
                    g_s = get_author_gender_from_ids_and_then_name_cached(conn, author.id,
                                                                          author.name)
                except UnableToDeriveGenderError as err:
                    # ...and if that fails, fall back to the name
                    pass # rely on "not g_s" to trigger the code a bit further down

            if not g_s and ( not author or author in ('uncredited',)):
                # Skip records without author e.g. AO3 in Hugo Best Related Work
                gender = 'unknown'
                try:
                    title_stuff = ' for "%s"' % book.title
                except AttributeError:
                    title_stuff = ''
                source = 'unknown:uncredited or undefined author%s' % (title_stuff)
                output_function('%s : %s : %s : %s' % (getattr(book, prefix_property),
                                                       gender, author, source))
                # TODO: next bit is copypasted from below, it shouldn't be duplicated
                gender_appearance_counts[gender] += 1
                year_gender_source_appearance_counts[(getattr(book, prefix_property),
                                                      gender)] += 1

                ignored.append(author)
                continue
            try:
                if not g_s:
                    if isinstance(author, tuple):
                        name = author.name
                    else:
                        name = author
                    # g_s = get_author_gender(conn, [name])
                    g_s = get_author_gender_cached(conn, [name])

                gender = g_s.gender or 'unknown'
                output_function('%s : %s : %s : %s' % (getattr(book, prefix_property),
                                                       gender, name, g_s.source))
                gender_appearance_counts[gender] += 1
                if gender and gender != 'unknown':
                    source_base = g_s.source.split(':')[0]
                    gender_source_appearance_counts[gender, source_base] += 1
                    year_gender_source_appearance_counts[(getattr(book, prefix_property),
                                                          gender, source_base)] += 1

                else:
                    year_gender_source_appearance_counts[(getattr(book, prefix_property),
                                                          gender)] += 1
                author_gender[author] = gender
            except AmbiguousArgumentsError as err:
                # "Mischa" in Clark Award 1991ish
                logging.warning('Skipping unknown author: %s' % (err))
                gender = 'unknown'
                author_gender[author] = 'unknown'
                gender_appearance_counts[gender] += 1
                year_gender_source_appearance_counts[(getattr(book, prefix_property),
                                                      gender)] += 1

                ignored.append(author)

    # num_processed_books = len(books) - len(ignored)

    author_gender_counts = Counter(author_gender.values())

    return GenderStats(gender_appearance_counts, gender_source_appearance_counts,
                       year_gender_source_appearance_counts, author_gender_counts)


def report_gender_analysis(gender_appearance_counts,
                           gender_source_appearance_counts,
                           year_gender_source_appearance_counts,
                           author_gender_counts,
                           output_function=print):
    """
    Output some stats, typically in the context of a standalone script.
    """

    denom = sum(gender_appearance_counts.values())
    output_function('\n= Total (by number of works) =')
    for k, v in gender_appearance_counts.most_common():
        output_function('%-10s : %3d (%d%%)' % (k, v, 100 * v / denom))


    denom = sum(gender_source_appearance_counts.values())
    output_function('\n= Total gender by source (by number of works, excludes unknowns) =')
    for k, v in gender_source_appearance_counts.most_common():
        output_function('%-10s : %3d (%d%%)' % (k, v, 100 * v / denom))


    denom = sum(author_gender_counts.values())
    output_function('\n= Total (by number of authors) =')
    for k, v in author_gender_counts.most_common():
        output_function('%-10s : %3d (%d%%)' % (k, v, 100 * v / denom))


def no_output(*args, **kwargs):
    pass

def year_data_as_cells(year_gender_source_appearance_counts,
                       first_column_heading='Year', output_function=no_output):
    """
    Return the year/gender/source (or any other property you might have
    chosen instead of year) in a form suitable for feeding into a CSVWriter,
    Google Sheets API, etc.

    Return value is a list of lists of data rows, with the first element
    being a list of column headings
    """

    # Note that these are somewhat "symmetrical" w.r.t. source ordering - this
    # is to make a stacked chart more aesthetically pleasing
    GENDER_HEADINGS_AND_KEYS = [
        GenderType('M (via Wikipedia)', ('M', 'wikipedia')),
        GenderType('M (via Twitter bio)', ('M', 'twitter')),
        GenderType('M (via human-names)', ('M', 'human-names')),

        GenderType('NB/GQ (via Wikipedia)', ('X', 'wikipedia')),
        GenderType('NB/GQ (via Twitter bio)', ('X', 'twitter')),

#        ('H (via Wikipedia)', ('H', 'wikipedia')), # House pseudonym - on hold for now
        GenderType('Unknown', ('unknown',)),

        GenderType('F (via human-names)', ('F', 'human-names')),
        GenderType('F (via Twitter bio)', ('F', 'twitter')),
        GenderType('F (via Wikipedia)', ('F', 'wikipedia'))
    ]

    ret = []

    output_function(',%s' % (','.join([z.heading for z in GENDER_HEADINGS_AND_KEYS])))
    headings = [first_column_heading]
    headings.extend([z.heading for z in GENDER_HEADINGS_AND_KEYS])
    ret.append(headings)

    years = set([z[0] for z in year_gender_source_appearance_counts.keys()])
    sortable_years = [y for y in years if (y and y != 8888)] # 8888 is a rogue value in ISFDB
    for y in sorted(sortable_years):
        vals = [y]
        for g in [z.key for z in GENDER_HEADINGS_AND_KEYS]:
            klist = [y]
            klist.extend(g)
            vals.append(year_gender_source_appearance_counts[tuple(klist)])
        ret.append(vals)
        output_function(','.join([str(z) for z in vals]))

    return ret
