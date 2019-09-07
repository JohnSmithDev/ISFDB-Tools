#!/usr/bin/env python3

from collections import Counter


from award_related import extract_authors_from_author_field
from author_gender import get_author_gender

def analyse_authors(conn, books, output_function=print, prefix_property='year',
                    csv_output=None):
    """
    Given a list of objects that have an author property, output some stats
    about author genders.
    """

    gender_appearance_counts = Counter()
    gender_source_appearance_counts = Counter()
    year_gender_source_appearance_counts = Counter()
    author_gender = {}
    ignored = []
    years = set()
    for book in books:
        for author in extract_authors_from_author_field(book.author):
            years.add(getattr(book, prefix_property))
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

    num_processed_books = len(books) - len(ignored)

    output_function('\n= Total (by number of works) =')
    for k, v in gender_appearance_counts.most_common():
        output_function('%-10s : %3d (%d%%)' % (k, v, 100 * v / num_processed_books))


    output_function('\n= Total gender by source (by number of works, excludes unknowns) =')
    for k, v in gender_source_appearance_counts.most_common():
        output_function('%-10s : %3d (%d%%)' % (k, v, 100 * v / num_processed_books))


    author_gender_counts = Counter(author_gender.values())
    output_function('\n= Total (by number of authors) =')
    for k, v in author_gender_counts.most_common():
        output_function('%-10s : %3d (%d%%)' % (k, v, 100 * v / len(author_gender)))

    # pdb.set_trace()
    # print(year_gender_source_appearance_counts)
    output_function(',M (via Wikipedia),M (via Twitter bio),M (via human-names),'
          'unknown,'
          'F (via Wikipedia),F (via Twitter bio),F (via human-names),')
    for y in sorted(years):
        vals = [y]
        for g in [('M', 'wikipedia'), ('M', 'twitter'), ('M', 'human-names'),
                  ('unknown',),
                  ('F', 'wikipedia'), ('F', 'twitter'), ('F', 'human-names')]:
            klist = [y]
            klist.extend(g)
            #print(y, g, year_gender_source_appearance_counts[tuple(klist)])
            vals.append(year_gender_source_appearance_counts[tuple(klist)])
        output_function(','.join([str(z) for z in vals]))
