#!/usr/bin/env python3


def derive_country_from_price(raw_price):
    if not raw_price:
        return None
    price = raw_price.upper()
    if price[0] == '$':
        return 'us' # What oz, etc?
    elif price.startswith('C$'):
        return 'ca'
    elif price[0] == '\xa3':
        return 'uk' # arguably it should be gb as per GBP, but whatever...
    elif re.match('\d+/[\d\-]+', price):
        return 'uk' # Pre-decimalization
    elif price[0] == '\x80':
        return 'eu' # Not a country, but will have to do
    else:
        logging.error('Dunno know what country price "%s" refers to' % (price))
        # pdb.set_trace()
        return None

# Surely there's an open source version of this?
country2code = {
    'USA': 'us',
    'Canada': 'ca',

    'China': 'cn',
    'Japan': 'jp',
    'Australia': 'oz',
    'Malaysia': 'my',
    'Singapore': 'sg',
    'India': 'in',

    'UK': 'uk',
    'England': 'uk',
    'Scotland': 'uk',
    'Wales': 'uk',
    'Northern Ireland': 'uk',
    'Ireland': 'ie',
    'Finland': 'fi',
    'West Germany': 'de',
    'East Germany': 'de',
    'Germany': 'de',
    'German Empire': 'de',
    'Holy Roman Empire': 'de', # This is dubious
    'French Fourth Republic': 'fr', # Or maybe de?  See Wolfgang Brenner/280988
    'Austria': 'au',
    'Austro-Hungarian Empire': 'au', # This is dubious
    'Czechoslovakia': 'cz', # Or could be sv?
}

def get_country(author_birthplace):
    if not author_birthplace:
        return None
    _, country_bit = author_birthplace.rsplit(',', 1)
    clean_country = country_bit.strip()

    # pdb.set_trace()
    try:
        return country2code[clean_country]
    except KeyError:
        logging.warning('Country "%s" unrecognized (from %s)' % (clean_country, author_birthplace))
        return None
