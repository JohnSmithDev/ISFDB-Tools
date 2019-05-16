#!/usr/bin/env python3
"""
Generic functions related to countries

"""

import csv
import logging
import pdb
import os
import re

TWO_CHAR_PRICE_PREFIXES = {
    'C$': 'CA',
    'A$': 'AU',
    'R$': 'BR', # Brazilian real
    'DM': 'DE'
}

def derive_country_from_price(raw_price, ref=None):
    """
    Given a string containing a price, return a 2-character country code, or
    None if one could not be derived.
    """
    # Unfortunately currency *symbols* don't seem to be in the CSV
    if not raw_price:
        return None
    price = raw_price.upper()
    price2ch = price[:2]

    if price2ch in TWO_CHAR_PRICE_PREFIXES:
        return TWO_CHAR_PRICE_PREFIXES[price2ch]
    if price[0] == '$':
        return 'US' # Q: Is a naked $ ever used for CA, AU, etc?
    elif price.startswith('CX$'): # http://www.isfdb.org/cgi-bin/pl.cgi?617032 - poss error?
        return 'CA'
    elif price.startswith('AU$'):
        return 'AU'
    elif (price[0] == '\xa3' or # pound sterling symbol
          re.match('\d+P', price)): # pence
        return 'GB'
    elif re.match('\d+/[\d\-]+', price) or \
         re.match('\-/[\d\-]+', price) or \
         re.match('\d+D', price):
        return 'GB' # Pre-decimalization
    elif price.startswith('HUF') or \
         price.endswith('FT'): # Hungarian forint
        return 'HU'
    elif price.startswith('Z&#322;'): # Polish zloty
        return 'PL'
    elif price.startswith('KN'): # Croatian kuna
        return 'HR'
    elif price.startswith('K&#269;'): # Czech koruna
        return 'CZ'
    elif price.startswith('LEV'): # Bulgarian Lev
        return 'BG'
    elif price.startswith('NIS'): # Israeli new shekel
        return 'IL'
    #elif price.startswith('DM'):
    #    return 'DE'
    elif price[0] == '\x83': # Pre-Euro - used on an edition of Ringworld
        return 'NL' # Guilder - apparently symbol is derived from Florin
    elif price[0] == 'F': # Pre-Euro - used on an edition of Ringworld
        return 'FR' # Franc
    elif price.endswith('LIT'): # Pre-Euro - used on an edition of Ringworld
        return 'IT' # Lira
    elif price[0] == '\x80': # Euro symbol
        return 'EU' # Not a country, but will have to do
    elif price[0] == '\xa5': # Japanese yen symbol
        return 'JP' # Q: Could this be Chinese Yuan (renminbi) also?
    elif price.startswith('&#20803;') or \
         price.endswith('&#20803;'): # Chinese renminbi/yuan
        return 'CN'
    elif price[0] == 'R':
        return 'ZA' # Rand?  See http://www.isfdb.org/cgi-bin/title.cgi?2422094
    elif price.startswith('&#8377;'): # HTML entity for rupee - http://www.isfdb.org/cgi-bin/pl.cgi?643560
        return 'IN'
    else:
        logging.error('Dunno know what country price "%s" refers to (ref=%s)' % \
                      (price, ref))
        # pdb.set_trace()
        return None


# These are historical, slight variations on what's in the country code file,
# etc.
# TODO (probably): move these into their own file, possibly JSON for wider
#                  reusability
COUNTRY_CODE_HACKS = {
    'West Germany': 'DE',
    'East Germany': 'DE',
    'Germany': 'DE',
    'German Empire': 'DE', # Is this the same as 'Greater Germany'?
    'Holy Roman Empire': 'DE', # This is dubious
    'Vienna': 'AT', # "Vienna, Ostmark, Greater Germany"

    'French Fourth Republic': 'FR', # Or maybe de?  See Wolfgang Brenner/280988
    'Grand Duchy of Finland': 'FI',
    'Kingdom of Belgium': 'BE',

    'British India': 'IN',
    'Persia': 'IR',

    'Union of South Africa': 'ZA',
    'Orange Free State': 'ZA',
    'Portuguese West Africa': 'AO', # https://en.wikipedia.org/wiki/Portuguese_Angola
    'French Algeria': 'DZ',

    # Not sure if these are in any ISFDB data, but adding them just in case
    # Note that ISO3166 Alpha-2 uses GB rather than UK :-|
    'England': 'GB',
    'Scotland': 'GB',
    'Wales': 'GB',
    'Northern Ireland': 'GB',

    # These are 'the Czech Republic' or 'Czechia' in the CSV
    'Czechoslovakia': 'CZ', # Or could be sv?
    'Czech Republic': 'CZ',

    'Russian Empire': 'RU',

    'US Virgin Islands': 'VB', # "U.S. Virgin Islands" or "United States..." in the CSV

    'Allentown': 'US', # Carmen Maria Machado entry lacks country
    'Andalusia': 'ES', # Marian Womack entry lacks country

    # More to add...

}

def get_country_name_to_code_mappings(filename=None):
    if not filename:
        filename = os.path.join(os.path.dirname(__file__),
                            'country-codes', 'data', 'country-codes.csv')
    ret = {}
    with open(filename) as csvfile:
        reader = csv.DictReader(csvfile)
        for line_num, row in enumerate(reader, 1):
            # Hmm, ISO3166 uses "GB" rather than "UK" - not sure that's what I
            # want
            ret[ row['CLDR display name'] ] = row['ISO3166-1-Alpha-2']
            ret[ row['FIFA'] ] = row['ISO3166-1-Alpha-2']

    ret.update(COUNTRY_CODE_HACKS)
    return ret

country2code = get_country_name_to_code_mappings()

def get_country(location, ref=None):
    if not location:
        return None
    if ',' in location:
        country_bits = reversed(location.split(','))
    else:
        country_bits = [location]

    for cb in country_bits:
        clean_country = cb.strip()
        try:
            return country2code[clean_country]
        except KeyError:
            pass
    logging.warning('Country not found/recognized in "%s (ref=%s)"' %
                    (location, ref))
    return None



if __name__ == '__main__':
    # This is just for manual testing/checking
    CSV_FILE = os.path.join(os.path.dirname(__file__),
                            'country-codes', 'data', 'country-codes.csv')
    with open(CSV_FILE) as csvfile:
        reader = csv.DictReader(csvfile)
        for line_num, row in enumerate(reader, 1):
            print(line_num,
                  row['ISO3166-1-Alpha-2'],
                  row['FIPS'],
                  row['WMO'],
                  row['TLD'], # This seems to be *mostly*  same as ISO3166, but with . & lower case
                  row['CLDR display name'],
                  row['ISO4217-currency_alphabetic_code'],
                  row['ISO4217-currency_numeric_code'],
                  row['EDGAR']
            )



