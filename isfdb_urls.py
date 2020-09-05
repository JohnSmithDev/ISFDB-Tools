#!/usr/bin/env python3
"""
A collection of simple functions to return an ISFDB URL (TODO and/ror HTTP/XML
links?) based on an ID, or some other parameter(s).

The idea is that if ISFDB ever changes URL schema/domain/etc, only this module
needs to be updated.
"""

SITE = 'http://www.isfdb.org'

def title_url(title_id):
    return f'{SITE}/cgi-bin/title.cgi?{title_id}'


def title_link(title_id, content, raise_if_no_url=False):
    try:
        url = title_url(title_id)
    except Exception as err:
        if raise_if_no_url:
            raise err
        else:
            return content
    return f'<a href="{url}">{content}</a>'

def author_url(author_id):
    return f'{SITE}/cgi-bin/ea.cgi?{author_id}'

def series_url(series_id):
    return f'{SITE}/cgi-bin/pe.cgi?{series_id}'
