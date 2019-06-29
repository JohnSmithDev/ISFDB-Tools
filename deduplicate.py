#!/usr/bin/env python3
"""
A fairly consistent pattern is:
1. Get a bunch of rows via a SQL query
2. Postprocess the rows to remove/merge duplicates that theoretically might
   be doable in the SQL query, but are easier to do with Python  e.g. books
   with multiple authors or variant titles
3. Return the deduplicated rows as a list of objects (that can have additional
   properties added e.g. the SVG chart generation)

This module provides helpers for the middle step.
"""

from functools import reduce

class DuplicatedOrMergedRecordError(Exception):
    """
    Recommnedation: subclass this for your own objects - this might avoid
    confusion if you have objects composed of other objects (e.g. books->
    publications) that could each raise some variant of this exception).
    """
    pass



def make_list_excluding_duplicates(rows, class_,
                                   allow_duplicates=False,
                                   duplication_exception=DuplicatedOrMergedRecordError):
    def reducer_function(accumulator, new_value):
        if not accumulator:
            accumulator = []
        try:
            accumulator.append(class_(new_value,
                                      allow_duplicates=allow_duplicates))
        except duplication_exception:
            pass
        return accumulator

    return reduce(reducer_function, rows, None)

