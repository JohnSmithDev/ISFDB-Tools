#!/usr/bin/env python3
"""
Misc helper functions.

Anything that will be widely used (~90% of scripts) should go into common.py
"""

from datetime import date
import re

def pretty_list(lst, max_items=3, others_label='items'):
    """
    Given a list of things (doesn't matter what as long as they have __str__
    or __repr__ type behaviour), return a string of the form
    "foo, bar, baz and N others"
    * max_items includes the final "N others"
    * others_label could be stuff like 'other people'
    """

    # Hang on: I don't think there's a case where we'll use the singular
    # label - if we get down to one item (either on it's own, or in the
    # "... and" bit, then we display that item literally instead of "...
    # "and one other item".  Leave as-is for now but TODO: revisit
    if '/' in others_label:
        singular_label, plural_label = others_label.split('/')
    else:
        singular_label = plural_label = others_label

    if not lst:
        return ''
    lenl = len(lst)
    if lenl == 1:
        return '%s' % (lst[0])
    if max_items == 1:
        return '%d %s' % (lenl, plural_label)
    elif lenl == 2:
        # return '%s and %s' % lst # Not sure why this thows TypeError, oh well
        return '%s and %s' % (lst[0], lst[1])
    else:
        if lenl <= max_items:
            first_bit = ', '.join(['%s' % z for z in lst[:-1]])
            second_bit = lst[-1]
        else:
            first_bit = ', '.join(['%s' % z for z in lst[:max_items-1]])
            if lenl - max_items + 1 == 1:
                # I *think* this should never get called - TODO: write some tests to prove it
                label = singular_label
            else:
                label = plural_label
            second_bit = '%d other %s' % (lenl - max_items + 1, label)
        return '%s and %s' % (first_bit, second_bit)

def convert_dateish_to_date(txt, default=None):
    """
    0 days of month (and I suspect month) are possible in the database, but
    convert to None-ish by SQLAlchemy.  Here we fake them as 1st of month or
    January.

    Set default to something if you need to sort the output (and can't be bothered
    to do something like https://stackoverflow.com/questions/12971631/sorting-list-by-an-attribute-that-can-be-none
    """
    bits = [int(z) for z in txt.split('-')]
    if not bits[0]: # probably '0000-00-00':
        return default
    if bits[1] == 0:
        bits[1] = 1
    if bits[2] == 0:
        bits[2] = 1
    return date(*bits)

def plural(qty, noun, plural_form=None, number_length=None, pad=False):
    if number_length is None:
        number_format = '%d'
    else:
        number_format = '%%%dd' % (number_length)
    if not plural_form:
        plural_form = noun + 's'
    pad_length = len(plural_form) - len(noun)
    if pad:
        pad_spaces = ' ' * pad_length
    else:
        pad_spaces = ''
    if qty == 1:
        end_bit = '%s%s' % (noun, pad_spaces)
    else:
        end_bit = plural_form
    fmt = '%s %s' % (number_format, end_bit)
    return fmt % (qty)

def padded_plural(qty, noun, plural_form=None, number_length=None):
    return plural(qty, noun, plural_form, number_length, pad=True)


def pretty_nth(number):
    if 11 <= number <= 13:
        return '%dth' % number
    remainder = number % 10
    try:
        suffix = ['th', 'st', 'nd', 'rd'][remainder]
    except IndexError:
        suffix = 'th'
    return '%d%s' % (number, suffix)


# Q: prefices, suffices?
BOGUS_PREFIXES = ['The ']
BOGUS_SUFFIXES = [': A Novel', ' (Boxed)', ' (series)']

def generate_variant_titles(original_title):
    """
    Return a list of variant titles, based on removing any possibly unnecessary
    prefixes for suffixes.
    """
    variants = set([original_title])
    prev_len = 0

    while len(variants) != prev_len:
        prev_len = len(variants)
        to_add = set() # can't update variants whilst iterating over it
        for title in variants:
            for prefix in BOGUS_PREFIXES:
                if title.startswith(prefix):
                    clean = title[len(prefix):]
                    to_add.add(clean)
            for suffix in BOGUS_SUFFIXES:
                if title.endswith(suffix):
                    clean = title[:-len(suffix)]
                    to_add.add(clean)
        variants.update(to_add)
    return variants

def merge_similar_titles(titles):
    """
    Given a list (well, iterable) of titles, remove any that are too similar to
    others e.g. "Look to Windward" vs "Look To Windward"

    Currently this just does case insensitivity, potentially it could do:
    * Levenshtein distance or similar
    * Removal of meta text e.g. "The Difference Engine (Boxed)"
    """

    lc_dict = dict([(t.lower().strip(), t.strip()) for t in titles])
    to_remove = []

    def has_bogus_prefix(title):
        for prefix in BOGUS_PREFIXES:
            if title.startswith(prefix):
                clean_lc = title[len(prefix):].lower()
                if clean_lc in lc_dict:
                    return True
        else:
            return False

    def has_bogus_suffix(title):
        for suffix in BOGUS_SUFFIXES:
            if title.endswith(suffix):
                clean_lc = title[:-len(suffix)].lower()
                if clean_lc in lc_dict:
                    return True
        else:
            return False

    for title in titles:
        if has_bogus_prefix(title) or has_bogus_suffix(title):
            # Q: Does this blow up if there are multiple matches?
            del lc_dict[title.lower()]

    return lc_dict.values()


if __name__ == '__main__':
    # Some stubs for basic sanity testing
    print(generate_variant_titles('The Inverted World'))
    print(generate_variant_titles('The Wheel of Time (series)'))


