#!/usr/bin/env python3
"""
Hacky script to split up the dump into separate files per table.

This is to make it easier to find where a value comes from, which is a PITA
doing with grep/less/etc due to the long lines.
"""

import os
import re
import sys

DEFAULT_DUMP_FILE = "/mnt/sdb10/data_downloads/isfdb/cygdrive.20190622/c/ISFDB/Backups/backup-MySQL-55-2019-06-22"

OUTPUT_DIR = "/tmp"


def write_buffer(tbl, buf):
    output_filename = os.path.join(OUTPUT_DIR, '%s.sql' % (tbl))
    print('Writing %d lines to %s' % (len(buf), output_filename))
    with open(output_filename, 'w') as outputstream:
        for l in buf:
            outputstream.write(l)
            outputstream.write('\n')


def split_dump(dump_file, output_dir):

    current_table = '_prologue'
    buf = []
    for line in open(dump_file):
        if line.startswith('LOCK TABLES'):
            if buf:
                write_buffer(current_table, buf)
            buf = [line]
            tablename_regex = re.search('LOCK TABLES `(\w+)`', line)
            if not tablename_regex:
                raise Exception('Unable to parse %s for table name' % (line))
            current_table = tablename_regex.group(1)
        elif line.startswith('UNLOCK TABLES'):
            # Do we need to do anything?  Only if we care about the epilogue
            # being table independent I think
            buf.append(line)
        else:
            buf.append(line)
    if buf:
        write_buffer(current_table, buf)



if __name__ == '__main__':
    if len(sys.argv) > 1:
        dump_file = sys.argv[1]
    else:
        dump_file = DEFAULT_DUMP_FILE
    split_dump(dump_file, OUTPUT_DIR)
