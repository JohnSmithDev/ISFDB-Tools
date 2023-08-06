#!/usr/bin/env python3
"""
Submit a batch of edits via the API to fix broken Amazon images, update domain names, etc.

cf https://isfdb.org/wiki/index.php/User_talk:Ahasuerus#Weird_broken_Amazon_image_URLs

Usage:

ISFDB_USERNAME=whatever ISFDB_WEB_API_KEY=whatever tools/submit_edits_via_api.py 0 20

(You probably want to make ISFDB_USERNAME and ISFDB_WEB_API_KEY environment variables, so
that you don't have to specify them each time.)

The first argument is an offset into the list of matching records, the second is the number
of records to process.  It's best to keep to no more than batches of 20-25 submitted edits,
and to get them accepted into ISFDB before doing another batch.
"""

import os
import pdb
import re
import sys
import time
from urllib.parse import urlparse

import requests
from sqlalchemy.sql import text
import untangle # https://github.com/stchris/untangle

from common import get_connection

# USERNAME = 'ErsatzCulture'
USERNAME = os.environ['ISFDB_USERNAME']

API_KEY = os.environ['ISFDB_WEB_API_KEY']
API_URL = 'https://www.isfdb.org/cgi-bin/rest/submission.cgi'

PAUSE_BETWEEN_REQUESTS = 5 # in seconds

class ISFDBWebAPIError(Exception):
    """
    This is just for 'content' errors; bad HTTP responses should instead raise
    requests.exceptions.HTTPError
    """
    pass

###
### Publication image fixes
###

def get_bad_pub_records(conn, offset, qty):

    query = text("""select pub_id, pub_title, pub_frontimage
    from pubs where pub_frontimage like '%imagerendering%'
    order by pub_id LIMIT :qty OFFSET :offset;""")

    params = {'qty': qty, 'offset': offset}
    results = conn.execute(query, params).fetchall()

    return results

def generate_pubupdate_imagefix(pid, subject, bad_image_url):
    good_image_url = re.sub('.W.IMAGERENDERING.*images', '', bad_image_url)
    if good_image_url == bad_image_url:
        raise Exception(f"Don't have to do anything with {bad_image_url} for {subject} ?")
    xml_text = f'''<?xml version="1.0" encoding="iso-8859-1" ?>
<IsfdbSubmission>
<PubUpdate>
<Record>{pid}</Record>
<Submitter>{USERNAME}</Submitter>
<LicenseKey>{API_KEY}</LicenseKey>
<Subject>{subject}</Subject>
<Image>{good_image_url}</Image>
<ModNote>Semi-automated fixing of bad Amazon image URLs</ModNote>
<Content>
</Content>
</PubUpdate>
</IsfdbSubmission>
'''
    return xml_text

###
### Author/title/etc webpage fixes
###


def get_bad_webpage_records(conn, offset, qty, column_name='author_id'):
    """
    Return a list of author_ids that need updating (or other IDs if you pass column_name)
    Note that a follow-up query has to be done to pull all that author's URLs, due to
    how AuthorUpdate edits work
    """
    # SQLAlchemy doesn't like you injecting column name with :column_name - I'm sure there
    # must be a way to do it that's more secure than {column_name} ?
    query = text(f"""SELECT DISTINCT {column_name} record_id
    FROM webpages
    WHERE url LIKE 'https://csfdb.scifi-wiki.com/%'
    AND {column_name} IS NOT NULL
    ORDER BY {column_name}
    LIMIT :qty OFFSET :offset;""")

    params = {'qty': qty, 'offset': offset, 'column_name': column_name}
    results = conn.execute(query, params).fetchall()
    # pdb.set_trace()
    return results


def DEPRECATED_get_author_urls(conn, author_id):
    """
    Return a list of URLs associated with an author.
    Also includes the author name as a convenience for populating the subject field of an
    edit submission
    """
    query = text("""SELECT a.author_id, a.author_canonical, w.url
    FROM authors a
    NATURAL JOIN webpages w
    WHERE a.author_id = :author_id;""")

    params = {'author_id': author_id}
    results = conn.execute(query, params).fetchall()
    return results


def get_urls(conn, record_id, table_name='authors', column_name='author_id',
             title_column_name='authors.author_canonical'):
    """
    Return a list of URLs associated with an record.  The returned rows includes the record
    title/lable/name as a convenience for populating the subject field of an edit submission.
    """

    # Note: We can't use NATURAL JOIN as the titles table has both title_id and series_id
    query = text(f"""SELECT {table_name}.{column_name}, {title_column_name} label, w.url
    FROM {table_name}
    LEFT OUTER JOIN webpages w ON w.{column_name} = {table_name}.{column_name}
    WHERE {table_name}.{column_name} = :record_id;""")

    params = {'record_id': record_id,
              'table_name': table_name,
              'column_name': column_name,
              'title_column_name': title_column_name}
    results = conn.execute(query, params).fetchall()
    return results


def get_title_urls(conn, title_id):
    return get_urls(conn, title_id, 'titles', 'title_id', 'title_title')

def get_author_urls(conn, author_id):
    return get_urls(conn, author_id, 'authors', 'author_id', 'author_canonical')


def generate_fixed_urls(conn, record_id, get_urls_function=get_author_urls):
    """
    Return 2-element tuple of (author name, list of fixed author URLs)

    BUG: URLs that have characters such as ampersand in will cause a server 400 error, as IIRC
    they need to be converted to &amp; entities for XML.
    """
    url_rows = get_urls_function(conn, record_id)
    ret = []
    for url_row  in url_rows:
        bits = urlparse(url_row.url)
        if bits.netloc == 'csfdb.scifi-wiki.com':
            # Using a protected method feels a bit yucky to me, but that's what
            # https://docs.python.org/3/library/urllib.parse.html does
            ret.append(bits._replace(netloc='csfdb.cn').geturl())
        else:
            ret.append(url_row.url)
    return url_rows[0].label, ret


def generate_update_webpages(record_id, subject, webpages, edit_type='AuthorUpdate'):
    """
    Note that webpages should include all the links associated with the record, including
    unchanged ones.
    """
    xml_text = [f'''<?xml version="1.0" encoding="iso-8859-1" ?>
<IsfdbSubmission>
<{edit_type}>
<Record>{record_id}</Record>
<Submitter>{USERNAME}</Submitter>
<LicenseKey>{API_KEY}</LicenseKey>
<Subject>{subject}</Subject>
<Webpages>
''']
    for url in webpages:
        xml_text.append(f'<Webpage>{url}</Webpage>\n')
    xml_text.append(f'''</Webpages>
<ModNote>Semi-automated fixing of updated CSFDB domain URLs</ModNote>
</{edit_type}>
</IsfdbSubmission>
''')
    return ''.join(xml_text)

###
###
###

def post_request(payload):
    # https://stackoverflow.com/questions/12509888/how-can-i-send-an-xml-body-using-requests-library
    headers = {'Content-Type': 'text/xml; charset="iso-8859-1"',
               'Host': urlparse(API_URL).netloc,
               # 'Content-Length': len(payload)
               }
    resp = requests.post(API_URL, data=payload, headers=headers)
    if not resp: # Requests will do __bool__ magic to be truthy or falsey in response to errors
        raise requests.exceptions.HTTPError(f'API returned HTTP error status {resp.status_code}')
    resp_obj = untangle.parse(resp.text)
    if resp_obj.ISFDB.Status.cdata != 'OK':
        raise ISFDBWebAPIError(f'API returned XML error response {resp_obj.text}')
    return resp.status_code


if __name__ == '__main__':
    try:
        offset = int(sys.argv[1])
    except: # naughty
        offset = 0

    try:
        quantity = int(sys.argv[2])
    except: # naughty
        quantity = 10

    mconn = get_connection()
    PUB_COVER_EDITS = """
    for i, row in enumerate(get_bad_pub_records(mconn, offset, quantity)):
        if i > 0:
            time.sleep(PAUSE_BETWEEN_REQUESTS)
        print(f'\n= {offset}+{i} =\n')
        subject = f'Image fix {offset+i} - ' + (re.sub('\W', '_', row.pub_title))

        # For now at least, don't catch any exceptions
        payload = generate_pubupdate_imagefix(row.pub_id, subject, row.pub_frontimage)
        print(payload)
        post_request(payload)
    """

    # This next one won't work as-is, due to subsequent function renamings and tweaks
    AUTHOR_CSFDB_EDITS = """
    for i, row in enumerate(get_bad_webpage_records(mconn, offset, quantity)):
        if i > 0:
            time.sleep(PAUSE_BETWEEN_REQUESTS)

        author_name, fixed_urls = generate_fixed_author_urls(mconn, row.author_id)

        print(f'\n= {offset}+{i} {author_name} =\n')
        subject = f'CSFDB URL fix {offset+i} - ' + (re.sub('\W', '_', author_name))

        # For now at least, don't catch any exceptions
        payload = generate_update_webpages(row.author_id, subject, fixed_urls)
        print(payload)
        post_request(payload)
    """

    for i, row in enumerate(get_bad_webpage_records(mconn, offset, quantity,
                                                    column_name='title_id' )):
        if i > 0:
            time.sleep(PAUSE_BETWEEN_REQUESTS)

        print(row.record_id)
        record_title, fixed_urls = generate_fixed_urls(mconn, row.record_id,
                                                       get_urls_function=get_title_urls)

        print(f'\n= {offset}+{i} {record_title} =\n')
        subject = f'CSFDB URL fix {offset+i} - ' + (re.sub('\W', '_', record_title))

        # For now at least, don't catch any exceptions
        payload = generate_update_webpages(row.record_id, subject, fixed_urls,
                                           edit_type='TitleUpdate')
        print(payload)
        post_request(payload)










