#!/usr/bin/env python3
"""
Given a title ID of an anthology or collection, generate data about the contents

Example usages and useful examples:

  ./analyze_anthology.py 33629 (this one has all original content)
  ./analyze_anthology.py 2013507 (this one one reprint and the rest original)
  ./analyze_anthology.py 2305932 (a 2018 year's best)
  ./analyze_anthology.py 2267599 (single author collection)

"""

from collections import defaultdict, Counter
import pdb
import sys


from sqlalchemy.sql import text

from common import get_connection
from title_publications import get_earliest_pub
from author_aliases import AuthorIdAndName

from title_contents import get_title_contents, analyse_pub_contents


def do_nothing(*args, **kwargs):
    """Stub for output_function argument override"""
    pass

def get_filtered_title_contents(conn, title_id):
    """
    Get the contents, excluding stuff that isn't of interest such as artwork and introductions
    """
    pub_contents = get_title_contents(conn, [title_id])
    best_pub_id, best_contents = analyse_pub_contents(pub_contents, output_function=do_nothing)
    return [z for z in best_contents
            if z['title_ttype'] not in {'ESSAY', 'COVERART', 'INTERIORART'}]


if __name__ == '__main__':
    conn = get_connection()

    for t in sys.argv[1:]:
        t_id = int(t)

        contents = get_filtered_title_contents(conn, t_id)

        for content_stuff in contents:
            earliest = get_earliest_pub(conn, [content_stuff['title_id']])
            # print(content_stuff, earliest)
            print('%s %40s was first published in %10s %s' % (content_stuff['title_ttype'],
                                                              content_stuff['title_title'],
                                                              earliest['pub_ctype'],
                                                              earliest['pub_title']))
