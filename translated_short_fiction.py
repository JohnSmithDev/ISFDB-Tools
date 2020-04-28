#!/usr/bin/env python3
"""
https://old.reddit.com/r/printSF/comments/g9m9bi/exploring_as_many_different_countrys_print_sf_as/
"""

from collections import namedtuple, defaultdict
import json
from os.path import basename, dirname
import os
import pdb
import sys

from sqlalchemy.sql import text

from common import (get_connection, parse_args, get_filters_and_params_from_args,
                    create_parser, AmbiguousArgumentsError)

# Possibly this isn't the complete list, but whatever...
FICTION_TYPES = ['COLLECTION', 'ANTHOLOGY', 'SHORTFICTION', 'NOVEL', 'OMNIBUS']


DEFAULT_TARGET_LANGUAGE = 17 # English

def get_translations_into(conn, to_lang):
    query = text("""
    SELECT t.title_id eng_id, t.title_title eng_title,
    CAST(t.title_copyright AS CHAR) eng_copyright,
    t.title_ttype, t.title_storylen,
    tp.title_id orig_id, tp.title_title orig_title,
    CAST(tp.title_copyright AS CHAR) orig_copyright,
    l.lang_name
    FROM titles t LEFT OUTER JOIN titles tp ON t.title_parent = tp.title_id
    LEFT OUTER JOIN languages l ON l.lang_id = tp.title_language
    WHERE t.title_language != tp.title_language
      AND t.title_ttype in :title_types
      AND t.title_language = :to_lang
    ORDER BY t.title_copyright DESC;""")

    results = conn.execute(query,
                           {'to_lang': to_lang, 'title_types': FICTION_TYPES}).fetchall()

    return results


def render(data, output_function=print):
    # Creating HTML like it's 199x...
    output_function('<!DOCTYPE html>')
    output_function('<html><head>')
    output_function('<meta charset="utf-8" />')
    output_function('<style>')
    output_function('* { font-family: Helvetica, Arial, sans-serif; }')
    output_function('thead { color: white; background: #444; }')
    output_function('tr:nth-child(even) { background: #eee; }')

    output_function('</style>')
    output_function('</head><body>')
    output_function('<h1>Short fiction translated into English</h1>')
    output_function('<p>Based on data stored in <a href="http://www.isfdb.org">ISFDB</a>.</p>')
    output_function('<p>Source code to generate this page is '
                    '<a href="https://github.com/JohnSmithDev/ISFDB-Tools/blob'
                    '/master/translated_short_fiction.py">here</a>.</p>')


    output_function('<table>')
    output_function('<thead><tr><th>English title</th><th>English pub/copyright date</th>')
    output_function('<th>Type</th><th>Original title</th>')
    output_function('<th>Original pub/copyright date</th>')
    output_function('<th>Original language</th>')
    output_function('</tr></thead>')
    output_function('<tbody>')

    for row in data:
        url = 'http://www.isfdb.org/cgi-bin/title.cgi?%d' % (row.eng_id)
        output_function(f'<tr><td><a href="{url}">{row.eng_title}</a></td>')
        if row.eng_copyright in ('0000-00-00', '8888-88-88', '8888-00-00'):
            e_pd = 'unknown'
        else:
            e_pd = row.eng_copyright
        output_function(f'<td>{e_pd}</td>')
        story_type = row.title_storylen or row.title_ttype.lower()
        output_function(f'<td>{story_type}</td>')
        orig_url = 'http://www.isfdb.org/cgi-bin/title.cgi?%d' % (row.orig_id)
        output_function(f'<td><a href="{orig_url}">{row.orig_title}</a></td>')
        if row.orig_copyright in ('0000-00-00', '8888-88-88', '8888-00-00'):
            o_pd = 'unknown'
        else:
            o_pd = row.orig_copyright
        output_function(f'<td>{o_pd}</td><td>{row.lang_name}</td>')
        output_function('</tr>')
        # print(row)
    output_function('</tbody></table>')
    output_function('</body><html>')

if __name__ == '__main__':
    if len(sys.argv) > 1:
        to_lang = int(sys.argv[1])
    else:
        to_lang = DEFAULT_TARGET_LANGUAGE

    conn = get_connection()
    data = get_translations_into(conn, to_lang)
    render(data)

