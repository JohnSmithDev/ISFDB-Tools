#!/usr/bin/env python3

import csv
import logging
import pdb
import os

def derive_country_from_price(raw_price):
    # Unfortunately currency *symbols* don't seem to be in the CSV
    if not raw_price:
        return None
    price = raw_price.upper()
    if price[0] == '$':
        return 'US' # What about Australia, etc?
    elif price.startswith('C$'):
        return 'CA'
    elif price[0] == '\xa3':
        return 'GB'
    elif re.match('\d+/[\d\-]+', price):
        return 'GB' # Pre-decimalization
    elif price[0] == '\x80':
        return 'EU' # Not a country, but will have to do
    else:
        logging.error('Dunno know what country price "%s" refers to' % (price))
        # pdb.set_trace()
        return None


# These are historical, slight variations on what's in the country code file,
# etc
COUNTRY_CODE_HACKS = {
    'West Germany': 'DE',
    'East Germany': 'DE',
    'Germany': 'DE',
    'German Empire': 'DE', # Is this the same as 'Greater Germany'?
    'Holy Roman Empire': 'DE', # This is dubious
    'Vienna': 'AT', # "Vienna, Ostmark, Greater Germany"

    'French Fourth Republic': 'FR', # Or maybe de?  See Wolfgang Brenner/280988
    'Grand Duchy of Finland': 'FI',

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

def get_country(location):
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
    logging.warning('Country not found/recognized in "%s"' % (location))
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



