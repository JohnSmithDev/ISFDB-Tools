#!/usr/bin/env python3

from __future__ import division

from collections import defaultdict, Counter
import json
import logging
import pdb
import re
import sys

from common import get_connection, parse_args, get_filters_and_params_from_args
from utils import pretty_list, padded_plural, pretty_nth
from finalists import get_type_and_filter, get_finalists
from author_country import get_author_country
from award_related import (extract_real_authors_from_author_field,
                           sanitise_authors_for_dodgy_titles)
from publication_history import get_title_details

from colorama_wrapper import Fore, Back, Style, COLORAMA_RESET

UNKNOWN_COUNTRY = '??'


# TODO: Add argument to override MAX_AUTHORS
MAX_AUTHORS = 3
# MAX_AUTHORS = 10

# TODO: make this configurable via command-line argument
EXCLUDED_AUTHORS = set(['Noah Ward'])


with open('hugo_nominations.json') as inputstream:
    HUGO_NOMINEES = json.load(inputstream)


def max_number_of_finalists(year, award=None):
    # TODO: something better
    if award == 'Hugo Award' and year >= 2017:
        return 6
    else:
        return 5

ROGUE_SERIES = -1
UNNUMBERED_SERIES_VOLUME = -99 # Be more explicit than 0 or None

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


def colourize(title_etc_tuple):
    try:
        title, volume_number, appearance_number = title_etc_tuple
    except ValueError as err:
        print('tuple is borked: %s (%s)' % (title_etc_tuple, err))
        pdb.set_trace()
    if volume_number:
        colour_code = SERIES_NUMBER_COLOUR[min(MAX_SERIES_NUMBER, volume_number)]
    else:
        colour_code = SERIES_NUMBER_COLOUR[None]
    if volume_number:
        tbit = '%s [%s]' % (title, volume_number)
    else:
        tbit = title

    if appearance_number and appearance_number > 1:
        nth = pretty_nth(appearance_number)
        tbit += ' (%s appearance for this series)' % (nth)

    return '%s%s%s' % (colour_code, tbit, COLORAMA_RESET)



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
    for year, category in sorted(finalist_data.keys()):
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
        for finalist, details in finalist_data[(year, category)]:
            series_id = None
            series_num = None
            ignore_this_one = False
            appearance_number = 0
            for title_details in details:
                # Q: Should we check series_id and/or title_seriesnum?
                # e.g. Provenance has the former but not the latter
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

        print('== %s %s ==' % (year, category))
        max_finalists = max_number_of_finalists(year)
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
    for vn, freq in volume_counter.most_common():
        vol_label = vn or 'Standalone'
        print('%-10s : %3d (%.1f%%)' % (vol_label, freq, 100 * freq / total_items))


def get_award_and_series(conn, args, level_filter):
    ret = defaultdict(list)
    award_results = get_finalists(conn, args, level_filter)

    for af in award_results:
        # The "not af.author" check should not be required, - removal of No
        # Award should be done in get_finalists (maybe with a switch arg)
        if not af.author or af.author in EXCLUDED_AUTHORS:
            continue
        # print(af)
        title_args = parse_args(['-A', af.author, '-T', af.title],
                                description='whatever')
        details = get_title_details(conn, title_args,
                                    ['series_id', 'title_seriesnum'])
        key = (af.year, af.category)
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

