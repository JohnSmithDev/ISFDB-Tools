#!/usr/bin/env python3
"""
Produce reports/aggregated data based on a list of book-like objects
"""

from collections import Counter
import pdb

from award_related import extract_authors_from_author_field
from author_gender import get_author_gender

def analyse_authors_by_gender(conn, books, output_function=print,
                              prefix_property='year'):
    """
    Given a list of objects that have an author property, return some aggregated
    stats about them, namely a tuple comprising four Counter objects:
    * By gender - key values are M, F, X or unknown
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
    ignored = []
    for book in books:
        for author in extract_authors_from_author_field(book.author):
            if author == 'uncredited':
                ignored.append(author)
                continue
            try:
                gender, source = get_author_gender(conn, [author])
                if not gender:
                    gender = 'unknown'
                output_function('%s : %s : %s : %s' % (getattr(book, prefix_property),
                                                       gender, author, source))
                gender_appearance_counts[gender] += 1
                if gender and gender != 'unknown':
                    source_base = source.split(':')[0]
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
                gender_appearance_counts['unknown'] += 1
                author_gender[author] = 'unknown'

    # num_processed_books = len(books) - len(ignored)

    author_gender_counts = Counter(author_gender.values())

    return (gender_appearance_counts, gender_source_appearance_counts,
            year_gender_source_appearance_counts, author_gender_counts)

def report_gender_analysis(gender_appearance_counts,
                           gender_source_appearance_counts,
                           year_gender_source_appearance_counts,
                           author_gender_counts,
                           output_function=print):


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
        ('M (via Wikipedia)', ('M', 'wikipedia')),
        ('M (via Twitter bio)', ('M', 'twitter')),
        ('M (via human-names)', ('M', 'human-names')),

        ('X (via Wikipedia)', ('X', 'wikipedia')),
        ('X (via Twitter bio)', ('X', 'twitter')),

        ('Unknown', ('unknown',)),

        ('F (via human-names)', ('F', 'human-names')),
        ('F (via Twitter bio)', ('F', 'twitter')),
        ('F (via Wikipedia)', ('F', 'wikipedia'))
    ]

    ret = []

    output_function(',%s' % (','.join([z[0] for z in GENDER_HEADINGS_AND_KEYS])))
    headings = [first_column_heading]
    headings.extend([z[0] for z in GENDER_HEADINGS_AND_KEYS])
    ret.append(headings)

    years = set([z[0] for z in year_gender_source_appearance_counts.keys()])
    for y in sorted(years):
        vals = [y]
        for g in [z[1] for z in GENDER_HEADINGS_AND_KEYS]:
            klist = [y]
            klist.extend(g)
            vals.append(year_gender_source_appearance_counts[tuple(klist)])
        ret.append(vals)
        output_function(','.join([str(z) for z in vals]))

    return ret
