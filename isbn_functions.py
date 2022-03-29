#!/usr/bin/env python3
"""
Functions for validating and manipulating ISBNs.

This code started off as copypastes from isbn.py and library.py in the ISFDB
code-svn repo, with minor tweaks for indentation, line length etc, plus some
explicit casting to int due to how Python3 returns floats when doing integer
division vs Python 2 keeping everything as - potentially rounded - ints.

I've added a helper function and a basic sanity check when run as a standalone
script.

Full license details for the original ISFDB code can be found here:

https://sourceforge.net/p/isfdb/code-svn/HEAD/tree/trunk/LICENSE

The copyright details from the header of library.py:

#     (C) COPYRIGHT 2007-2019   Al von Ruff, Ahasuerus and Dirk Stoecker
#       ALL RIGHTS RESERVED
#
#     The copyright notice above does not evidence any actual or
#     intended publication of such source code.

(ISFDB's isbn.py has the same header, albeit with an older year.)

"""

import re

def toISBN10(isbn13):
    if len(isbn13) != 13 or not isbn13.startswith('978'):
        return isbn13
    isbn = isbn13[3:12]
    counter = 0
    sum = 0
    mult = 1
    try:
        while counter < 9:
            sum += (mult * int(isbn[counter]))
            mult += 1
            counter += 1
        remain = sum % 11
        if remain == 10:
            isbn = isbn + 'X'
        else:
            isbn = isbn + str(remain)
        return isbn
    except:
        return isbn13

def toISBN13(isbn):
    if len(isbn) != 10:
        return isbn
    newISBN = '978' + isbn[0:9]

    try:
        sum1 = int(newISBN[0]) + int(newISBN[2]) + int(newISBN[4]) + \
               int(newISBN[6]) + int(newISBN[8]) + int(newISBN[10])
        sum2 = int(newISBN[1]) + int(newISBN[3]) + int(newISBN[5]) + \
               int(newISBN[7]) + int(newISBN[9]) + int(newISBN[11])
        checksum = sum1 + (sum2 * 3)
        remainder = checksum - (int(checksum/10)*10)
        if remainder:
            remainder = 10 - remainder
        newISBN = newISBN + str(remainder)
        return newISBN
    except:
        return isbn



def normalized_isbn13(txt):
    clean_txt = re.sub('[^0-9X]', '', txt)
    return toISBN13(clean_txt)


def isbn10and13(isbn):
    """
    This is basically a very cut-down version of isbn.isbnVariations in the
    real ISFDB code.
    """
    return [z for z in [toISBN10(isbn), toISBN13(isbn)] if z]

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        original = sys.argv[1]
    else:
        original = '1471146588'
    there = toISBN13(original)
    andbackagain = toISBN10(there)
    print(original, there, andbackagain)
