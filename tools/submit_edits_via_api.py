#!/usr/bin/env python3
"""
Submit some edits via the API to fix broken Amazon images

cf https://isfdb.org/wiki/index.php/User_talk:Ahasuerus#Weird_broken_Amazon_image_URLs

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


def get_bad_records(conn, offset, qty):

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
    for i, row in enumerate(get_bad_records(mconn, offset, quantity)):
        if i > 0:
            time.sleep(PAUSE_BETWEEN_REQUESTS)
        print(f'\n= {offset}+{i} =\n')
        subject = f'Image fix {offset+i} - ' + (re.sub('\W', '_', row.pub_title))

        # For now at least, don't catch any exceptions
        payload = generate_pubupdate_imagefix(row.pub_id, subject, row.pub_frontimage)
        print(payload)
        post_request(payload)















