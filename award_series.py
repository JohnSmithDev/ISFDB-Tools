#!/usr/bin/env python3

from __future__ import division

from collections import defaultdict, Counter
import json
import logging
import pdb
import re
import sys

from common import get_connection, parse_args
from utils import pretty_list, padded_plural, pretty_nth
from finalists import get_type_and_filter, get_finalists
from author_country import get_author_country
from award_related import (extract_real_authors_from_author_field, # Maybe not needed here?
                           extract_authors_from_author_field,
                           extract_variant_titles,
                           sanitise_authors_for_dodgy_titles)
from publication_history import get_title_details, discover_title_details

from colorama_wrapper import Fore, Back, Style, COLORAMA_RESET

UNKNOWN_COUNTRY = '??'


# TODO: Add argument to override MAX_AUTHORS
MAX_AUTHORS = 3
# MAX_AUTHORS = 10

# TODO: make this configurable via command-line argument
EXCLUDED_AUTHORS = set(['Noah Ward'])


with open('hugo_nominations.json') as inputstream:
    HUGO_NOMINEES = json.load(inputstream)
with open('award_category_to_title_ttypes.json') as inputstream:
    CATEGORY_TO_TTYPES = json.load(inputstream)


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



def get_best_remaining_nominees(qty, extant_finalists, rejected_finalists, all_nominees):
    ret = []
    known_titles = [z[0] for z in extant_finalists]
    known_titles.extend([z[0] for z in rejected_finalists])
    for nominee in all_nominees:
        if len(ret) == qty:
            break
        # print('Checking %s against %s' % (nominee, extant_finalists))
        if nominee not in known_titles:
            ret.append(nominee)
    return ret


def output_revised_finalists(finalist_data, reject_repeats=True):
    # BUG/TODO/QUESION: If for example, series X has been honoured in Best Novella,
    # should we allow it for Best Novel?  (e.g. Lady Astronaut)
    already_honoured_series = defaultdict(list) # Maps series ID to years honoured
    volume_counter = Counter()
    for ayc_key in sorted(finalist_data.keys()):
        award, year, category = ayc_key
        try:
            relevant_nominees = HUGO_NOMINEES[category][str(year)]
        except (KeyError) as err:
            # logging.warning('No nomination data for %s/%s' % (category, year))
            relevant_nominees = None

        FIRST_ATTEMPT = """
        # Hmm, got the finalists and nominees inoptimally structured
        # TODO: rework more efficiently
        # ... or maybe not
        actual_finalists = finalist_data[(year,category)]
        allowed_finalists = []
        for nominee in relevant_nominees:
            ignore_this_one = False
            for af in actual_finalists:
                if af[0].title == nominee:
                    for title_details in af[1]:
                        # Q: Should we check series_id and/or title_seriesnum?
                        # e.g. Provenance has the former but not the latter
                        series_id = title_details['series_id']
                        if not series_id:
                            pass
                        else:
                            if series_id not in already_honoured_series:
                                pass
                                already_honoured_series[series_id] = year
                            elif not title_details['title_seriesnum']:
                                # This is allowable e.g. Provenance
                                pass
                            else:
                                ignore_this_one = True
                                logging.warning('Ignoring %s - series=%d' % (af[0].title,
                                                                           series_id))
            if not ignore_this_one:
                allowed_finalists.append(nominee)
        """
        allowed_finalists = []
        rejected_finalists = []
        for finalist, details in finalist_data[ayc_key]:
            series_id = None
            series_num = None
            ignore_this_one = False
            appearance_number = 0
            if not details: # Ugly hack for now
                continue
            for title_details in [details]: # ugly hack due to changing return type elsewhere
                # Q: Should we check series_id and/or title_seriesnum?
                # e.g. Provenance has the former but not the latter
                print(title_details)
                series_id = title_details['series_id']
                series_num = title_details['title_seriesnum']
                if series_id and not series_num:
                    series_num = UNNUMBERED_SERIES_VOLUME
                if not series_id:
                    pass
                else:
                    if series_id not in already_honoured_series:
                        pass
                    elif series_num == UNNUMBERED_SERIES_VOLUME:
                        # This is allowable e.g. Provenance
                        pass
                    else:
                        ignore_this_one = True
                        # logging.warning('Ignoring %s - series=%d' % (finalist.title,
                        #                                            series_id))
                    already_honoured_series[series_id].append(year)
                    appearance_number = len(already_honoured_series[series_id])
            if reject_repeats and ignore_this_one:
                rejected_finalists.append((finalist.title, series_num, appearance_number))
            else:
                allowed_finalists.append((finalist.title, series_num, appearance_number))
            volume_counter[series_num] += 1

        print('== %s %s %s finalists/nominees/shortlist ==' % (award, year, category))
        # TODO: this function needs to know the award name
        max_finalists = max_number_of_finalists(year, award)
        # print(year, max_finalists)
        for allowed in allowed_finalists[:max_finalists]:
            print('* %s' % colourize(allowed))
        if reject_repeats and len(allowed_finalists) < max_finalists:
            if relevant_nominees:
                extras = get_best_remaining_nominees(max_finalists - len(allowed_finalists),
                                                     allowed_finalists,
                                                     rejected_finalists,
                                                     relevant_nominees)
                for extra in extras:
                    # TODO: lookup this so that we have real series details
                    print('* %s' % colourize((extra, ROGUE_SERIES, 0)))
            else:
                extras = []
            shortfall = max_finalists - (len(allowed_finalists) + len(extras))
            if shortfall:
                print('* ... plus %d others (%d rejected due to series prior appearance)' % \
                      (shortfall, len(rejected_finalists)))

        print()

    # pdb.set_trace()
    total_items = sum(volume_counter.values())
    MAX_LABEL_LEN = max([len(z) for z in VOLUME_LABELS.values()])
    print('= %s %s finalists/nominees/shortlist =' % (award, category))
    for vn, freq in volume_counter.most_common():
        # vol_label = vn or 'Standalone'
        try:
            vol_label = VOLUME_LABELS[vn]
        except KeyError:
            vol_label = 'Volume %d in a series' % (vn)
        fmt = '%%-%ds : %%3d (%%.1f%%%%)' % (MAX_LABEL_LEN)
        print(fmt % (vol_label, freq, 100 * freq / total_items))




def get_award_and_series(conn, args, level_filter):
    ret = defaultdict(list)
    award_results = get_finalists(conn, args, level_filter)

    for af in award_results:
        # The "not af.author" check should not be required, - removal of No
        # Award should be done in get_finalists (maybe with a switch arg)
        if not af.author or af.author in EXCLUDED_AUTHORS:
            continue
        # print(af)
        FIRST_ATTEMPT = """
        title_args = parse_args(['-A', af.author, '-T', af.title],
                                description='whatever')
        details = get_title_details(conn, title_args,
                                    ['series_id', 'title_seriesnum'])
        """
        authors = extract_authors_from_author_field(af.author)
        titles = extract_variant_titles(af.title)

        try:
            category_group = CATEGORY_TO_TTYPES[af.award]
        except KeyError:
            category_group = CATEGORY_TO_TTYPES['Default']
        try:
            ttypes = category_group[af.category]
        except KeyError:
            logging.warning('No type definition found for %s/%s - accepting anything' %
                            (af.award, af.category))
            ttypes = []

        # TODO: Similar for title variants
        details = discover_title_details(conn, authors, titles,
                                         ['series_id', 'title_seriesnum'],
                                         exact_match=True,
                                         title_types=ttypes)


        if not details:
            logging.warning('Failed to get details for %s/%s' % (authors, titles))
        key = (af.award, af.year, af.category)
        ret[key].append((af, details))
    return ret

if __name__ == '__main__':
    typestring, level_filter = get_type_and_filter('finalists')

    args = parse_args(sys.argv[1:],
                      description='Show %s for an award' % (typestring),
                      supported_args='cwy')

    conn = get_connection()
    finalists = get_award_and_series(conn, args, level_filter)
    output_revised_finalists(finalists, reject_repeats=False)

