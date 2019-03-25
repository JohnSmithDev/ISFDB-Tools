#!/usr/bin/env python3
"""
Misc helper functions.

Anything that will be widely (~90% of scripts) should o into common.py
"""


def pretty_list(lst, max_items=3, others_label='items'):
    """
    Given a list of things (doesn't matter what as long as they have __str__
    or __repr__ type behaviour), return a string of the form
    "foo, bar, baz and N others"
    * max_items include the final "N others"
    * others_label could be stuff like 'other people'
    """

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
        if lenl < max_items:
            first_bit = ', '.join(['%s' % z for z in lst[:-1]])
            second_bit = lst[-1]
        else:
            first_bit = ', '.join(['%s' % z for z in lst[:max_items-1]])
            if lenl - max_items == 1:
                label = singular_label
            else:
                label = plural_label
            second_bit = '%d other %s' % (lenl - max_items + 1, label)
        return '%s and %s' % (first_bit, second_bit)
