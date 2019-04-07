#!/usr/bin/env python3
"""
Misc helper functions.

Anything that will be widely (~90% of scripts) should o into common.py
"""

from datetime import date

def pretty_list(lst, max_items=3, others_label='items'):
    """
    Given a list of things (doesn't matter what as long as they have __str__
    or __repr__ type behaviour), return a string of the form
    "foo, bar, baz and N others"
    * max_items include the final "N others"
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

def convert_dateish_to_date(txt):
    """
    0 days of month (and I suspect month) are possible in the database, but
    convert to None-ish by SQLAlchemy.  Here we fake them as 1st of month or
    January.
    """
    bits = [int(z) for z in txt.split('-')]
    if not bits[0]: # probably '0000-00-00':
        return None
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
