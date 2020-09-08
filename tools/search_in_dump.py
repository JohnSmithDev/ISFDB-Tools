#!/usr/bin/env python3

import re
import sys


DUMP_FILE = '/mnt/sdb10/data_downloads/isfdb/cygdrive/c/ISFDB/Backups/backup-MySQL-55-2019-02-09'


def search_for(word):
    current_table = None
    for i, line in enumerate(open(DUMP_FILE), 1):
        # print(line[:100])
        table_check = re.match('\-\- (Table structure for table |Dumping data for table )`(.*)`',
                               line)
        if table_check:
            current_table = table_check.group(2)
            # print('Reference to table %s found at line %d' % (table_check.group(2),
            #                                                  i))
        if word in line:
            print('Found reference at line %d (current table %s)' %
                  (i, current_table))

if __name__ == '__main__':
    for word in sys.argv[1:]:
        search_for(word)
