#!/usr/bin/env python3
"""
Statistics on how many award nominees/finalists are series fiction.

This started off with a slightly different aim (what would finalists look
like if series could not make repeat appearances), which has been abandoned.
That code has been deleted, but it's in the Git history prior to 2020-02-14
"""

from __future__ import division

from collections import defaultdict, Counter
import json
import logging
import pdb
import re
import sys

from common import get_connection, parse_args
from isfdb_utils import (pretty_list, padded_plural, pretty_nth,
                         generate_variant_titles)
from finalists import get_type_and_filter, get_finalists
from author_country import get_author_country
from award_related import (EXCLUDED_AUTHORS, extract_variant_titles,
                           extract_authors_from_author_field)
from title_related import (get_title_details, discover_title_details,
                           get_title_details_from_id)

from colorama_wrapper import Fore, Back, Style, COLORAMA_RESET



# TODO: Add argument to override MAX_AUTHORS
MAX_AUTHORS = 3
# MAX_AUTHORS = 10


with open('award_nominations.json') as inputstream:
    AWARD_NOMINEES = json.load(inputstream)
with open('award_category_to_title_ttypes.json') as inputstream:
    CATEGORY_TO_TTYPES = json.load(inputstream)

# This should be removed
def max_number_of_finalists(year, award=None):
    # TODO: something better
    if award == 'Hugo Award' and year >= 2017:
        return 6
    else:
        return 5

ROGUE_SERIES = -1
UNNUMBERED_SERIES_VOLUME = -99 # e.g. Provenance

SERIES_NUMBER_COLOUR = {
    None: Fore.WHITE,
    1: Fore.LIGHTYELLOW_EX,
    2: Fore.LIGHTGREEN_EX,
    3: Fore.LIGHTCYAN_EX,
    4: Fore.LIGHTBLUE_EX,
    5: Fore.LIGHTMAGENTA_EX,
    ROGUE_SERIES: Back.RED,
    UNNUMBERED_SERIES_VOLUME: Fore.LIGHTRED_EX
}
MAX_SERIES_NUMBER = max([z for z in SERIES_NUMBER_COLOUR.keys() if z])
# Hmm, this could maybe be a list with a separate fallback value if we really
# need it?
APPEARANCE_NUMBER_COLOUR = {
    None: Back.RESET,
    0: Back.BLACK,
    1: Back.LIGHTBLACK_EX,
    2: Back.MAGENTA,
    3: Back.BLUE,
    4: Back.LIGHTBLUE_EX,
    5: Back.CYAN,
    6: Back.GREEN,
    7: Back.LIGHTGREEN_EX
}
MAX_APPEARANCE_NUMBER = max([z for z in APPEARANCE_NUMBER_COLOUR.keys() if z])

VOLUME_LABELS = {
    None: 'Completely standalone',
    UNNUMBERED_SERIES_VOLUME: 'Standalone, but part of a universe/overarching series'
}

def colourize(title_etc_tuple):
    try:
        title, volume_number, appearance_number = title_etc_tuple
    except ValueError as err:
        logging.error('tuple is borked: %s (%s)' % (title_etc_tuple, err))
        pdb.set_trace()
    if volume_number:
        colour_code = SERIES_NUMBER_COLOUR[min(MAX_SERIES_NUMBER, volume_number)]
    else:
        colour_code = SERIES_NUMBER_COLOUR[None]
    if volume_number:
        tbit = '%s [%s]' % (title, volume_number)
    else:
        tbit = title

    appearance_code = APPEARANCE_NUMBER_COLOUR.get(appearance_number, Back.RESET)
    if appearance_number and appearance_number > 1:
        nth = pretty_nth(appearance_number)
        abit = ' %s(%s appearance for this series)' % (appearance_code, nth)
    else:
        abit = ''

    return '%s%s%s%s%s' % (colour_code, tbit, COLORAMA_RESET, abit, COLORAMA_RESET)






def output_revised_finalists(finalist_data,
                             output_function=print):
    # BUG/TODO/QUESION: If for example, series X has been honoured in Best Novella,
    # should we allow it for Best Novel?  (e.g. Lady Astronaut)
    already_honoured_series = defaultdict(list) # Maps series ID to years honoured
    volume_counter = Counter()
    for ayc_key in sorted(finalist_data.keys()):
        award, year, category = ayc_key
        try:
            relevant_nominees = AWARD_NOMINEES[award][category][str(year)]
        except (KeyError) as err:
            # logging.warning('No nomination data for %s/%s' % (category, year))
            relevant_nominees = None

        allowed_finalists = []
        for finalist, title_details in finalist_data[ayc_key]:
            series_id = None
            series_num = None
            appearance_number = 0
            if not title_details: # Ugly hack for now
                continue
            # Q: Should we check series_id and/or title_seriesnum?
            # e.g. Provenance has the former but not the latter
            logging.debug('title_details: %s' % (title_details))
            series_id = title_details['series_id']
            series_num = title_details['title_seriesnum']
            if series_id and not series_num:
                # print(finalist, series_id, series_num)
                series_num = UNNUMBERED_SERIES_VOLUME
            if not series_id:
                pass
            else:
                already_honoured_series[series_id].append(year)
                appearance_number = len(already_honoured_series[series_id])
            allowed_finalists.append((finalist.title, series_num, appearance_number))
            volume_counter[series_num] += 1

        output_function('== %s %s %s finalists/nominees/shortlist ==' % (award, year, category))
        # TODO: Revisit this "trimming"/replacement concept, it should instead
        # be based on the number of finalists we had to start with
        max_finalists = max_number_of_finalists(year, award)

        # print(year, max_finalists)
        # for allowed in allowed_finalists[:max_finalists]:
        for allowed in allowed_finalists:
            output_function('* %s' % colourize(allowed))
        output_function()

    render_count_summary(award, category, volume_counter, output_function)


def render_count_summary(award, category, volume_counter, output_function=print):
    total_items = sum(volume_counter.values())
    MAX_LABEL_LEN = max([len(z) for z in VOLUME_LABELS.values()])
    output_function('= %s %s finalists/nominees/shortlist =' % (award, category))
    for vn, freq in volume_counter.most_common():
        try:
            vol_label = VOLUME_LABELS[vn]
        except KeyError:
            vol_label = 'Volume %d in a series' % (vn)
        fmt = '%%-%ds : %%3d (%%.1f%%%%)' % (MAX_LABEL_LEN)
        output_function(fmt % (vol_label, freq, 100 * freq / total_items))


def get_award_and_series(conn, args, level_filter):
    ret = defaultdict(list)
    award_results = get_finalists(conn, args, level_filter)

    for af in award_results:
        # The "not af.author" check should not be required, - removal of No
        # Award should be done in get_finalists (maybe with a switch arg). TODO: implement that
        if not af.author or af.author in EXCLUDED_AUTHORS:
            continue

        # Next bit of code was intended for Hugo/Wheel of Time - but fails
        # because Wheel of Time isn't a book name, so I'll need a different
        # approach.
        MIGHT_BE_USEFUL_ONE_DAY = """
        if not af.title_id:
            possible_titles = set()
            for base_title in extract_variant_titles(af.title):
                possible_titles.update(generate_variant_titles(af.title))
            possible_authors = extract_authors_from_author_field(af.author)
            stuff = discover_title_details(conn, possible_authors, possible_titles)
            pdb.set_trace()
        """

        details = get_title_details_from_id(conn, af.title_id,
                                            extra_columns=['series_id', 'title_seriesnum'],
                                            parent_search_depth=5)
        if not details:
            # Example: Paul Kincaid special Clarke Award in 2006.  This wouldn't
            # be a problem except for the Clarke is (currently) semi-borked with
            # weird Winner vs Nominees vs Runnerup categories.  UPDATE: I think
            # the Clarke data is now fixed
            logging.warning('Failed to get details for title_id=%s (%s/%s)' %
                            (af.title_id, af.author, af.title))
        else:
            key = (af.award, af.year, af.category)
            ret[key].append((af, details))
    return ret


if __name__ == '__main__':
    typestring, level_filter = get_type_and_filter('finalists')

    args = parse_args(sys.argv[1:],
                      description='Show how serialized work appears in the %s for an award' %
                      (typestring),
                      supported_args='cwy')

    conn = get_connection()
    finalists = get_award_and_series(conn, args, level_filter)
    output_revised_finalists(finalists)

