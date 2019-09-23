#!/usr/bin/env python3
"""
Download and persist to filesystem content at URLs.  Includes functionality for:
* Optionally not downloading if data already exists
* Throttling of requests to the same domain
* Sanitising URL paths for filesystem
* etc
"""

from datetime import datetime
from enum import Enum
import logging
import os
import pdb
import re
import sys
import time

import requests
from urllib.parse import urlparse


class OverwriteBehaviour(Enum):
    OVERWRITE = 0
    NEVER_OVERWRITE = 1
    RENAME_OLD_WITH_TIMESTAMP_SUFFIX = 2

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), 'download_cache')

THROTTLE_SECONDS = 5
throttled_domains = {} # maps sanitised domain/hostname to time of last download


class UnableToSaveError(Exception):
    pass
class CannotOverwriteError(Exception):
    # https://stackoverflow.com/questions/1319615/proper-way-to-declare-custom-exceptions-in-modern-python/1319675#1319675
    def __init__(self, message, extant_file):
        super().__init__(message)
        self.extant_file = extant_file

def sanitised_filename_for_url(url):
    def sanitise(txt):
        return re.sub('[^\w\.]', '_', txt)

    bits = urlparse(url)
    filename = sanitise(bits.path)
    if bits.params:
        filename += '_' + sanitise(bits.params)
    if bits.fragment:
        filename += '_' + sanitise(bits.fragment)

    return bits.hostname, filename

def file_datestring(fn, delimiter='-'):
    # Note: using mtime ratehr than ctime - ctime is *not* the creation time,
    # it is the metadata change time, and can be newer than the mtime
    extant_time = time.localtime(os.stat(fn).st_mtime)
    fmt = delimiter.join(['%Y', '%m', '%d'])
    dt = time.strftime(fmt, extant_time)
    return dt


def rename_with_timestamp_suffix(full_path, dont_die_if_doesnt_exist=True):
    # TODO (nice-to-have/optional): keep any file type suffix
    # e.g. rename foo.txt to foo_20190531123456.txt rather than
    # foo.txt_201905311233456
    if dont_die_if_doesnt_exist and not os.path.exists(full_path):
        return
    extant_ctime = time.localtime(os.stat(full_path).st_ctime)
    ts = time.strftime('%Y%m%d%H%M%S', extant_ctime)
    os.rename(full_path, full_path + '_' + ts)

def download_file_as(url, full_path, overwrite):
    """
    Download file to a specific location - this is primarily intended for
    "internal use" by download_file(), but might be useful for downloads outside
    of the usual context, but where you still want to use the throttling and/or
    overwrite logic.
    """
    domain, _= sanitised_filename_for_url(url)

    # Check for existing files before doing downloads, if for no reason other
    # than avoiding unnecessary throttling
    if os.path.exists(full_path) and overwrite == OverwriteBehaviour.NEVER_OVERWRITE:
        raise CannotOverwriteError('Cannot overwrite existing file %s' %
                                   (full_path), extant_file=full_path)

    if THROTTLE_SECONDS > 0: # Q: Will things work OK without this doing check?
        now = datetime.now()
        try:
            previous = throttled_domains[domain]
            difference = (now - previous).total_seconds()
            if difference < THROTTLE_SECONDS:
                pause_for = THROTTLE_SECONDS - difference
                logging.debug('Throttling request to %s for %.2f seconds' %
                              (domain, pause_for))
                time.sleep(pause_for)

        except KeyError:
            # Domain hasn't been previously downloaded from, so no need to
            # throttle or do anything
            pass

    req = requests.get(url)
    throttled_domains[domain] = datetime.now()
    if req.ok:
        # logging.error("Status code = %s" % (req.status_code))

        if os.path.exists(full_path):
            if overwrite == OverwriteBehaviour.OVERWRITE:
                pass
            elif overwrite == OverwriteBehaviour.NEVER_OVERWRITE:
                # This check was done earlier, but I'll keep it here for
                # belt-and-braces safety
                raise CannotOverwriteError('Cannot overwrite existing file %s' %
                                           (full_path), extant_file=full_path)
            else:
                rename_with_timestamp_suffix(full_path)

        content = req.content
        # logging.error('Received %s (%d bytes)' % (full_path, len(content)))
        with open(full_path, 'wb') as outputstream:
            outputstream.write(content)
        logging.info('Wrote %s (%d bytes)' % (full_path, len(content)))
        return full_path
    else:
        raise UnableToSaveError('Got HTTP %s when getting %s' % (req.status_code,
                                                                 url))


def download_file(url, overwrite=OverwriteBehaviour.RENAME_OLD_WITH_TIMESTAMP_SUFFIX):
    subdir, filename = sanitised_filename_for_url(url)
    full_dir = os.path.join(DOWNLOAD_DIR, subdir)
    if not os.path.exists(full_dir):
        os.mkdir(full_dir)
    full_path = os.path.join(full_dir, filename)

    return download_file_as(url, full_path, overwrite)

def download_file_only_if_necessary(url):
    # TODO: optionally redownload and overwrite files over a user-specified age?
    #       Maybe that should be in download_file()?
    try:
        fn = download_file(url, overwrite=OverwriteBehaviour.NEVER_OVERWRITE)
    except CannotOverwriteError as err:
        logging.debug('Already downloaded %s as %s' % (url, err.extant_file))
        fn = err.extant_file
    return fn

if __name__ == '__main__':
    details = download_file(sys.argv[1])
    print('Saved as %s' % (details))

