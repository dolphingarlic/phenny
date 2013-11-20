#!/usr/bin/python3
"""
ethnologue.py - Ethnologue.com language lookup
author: mattr555
"""

#from modules.iso639 import ISOcodes
from lxml import html
import urllib.request
from urllib.error import HTTPError
from string import ascii_lowercase
import os

def shorten_num(n):
    if n < 1000:
        return '{:,}'.format(n)
    elif n < 1000000:
        return '{:.0f}K'.format(round(n/1000, 1))
    elif n < 1000000000:
        return '{:.0f}M'.format(round(n/1000000, 1))

def scrape_ethnologue_codes():
    data = {}
    base_url = 'http://www.ethnologue.com/browse/codes/'
    for letter in ascii_lowercase:
        resp = urllib.request.urlopen(base_url + letter).read()
        h = html.document_fromstring(resp)
        for e in h.find_class('views-field-field-iso-639-3'):
            code = e.find('div/a').text
            name = e.find('div/a').attrib['title']
            data[code] = name
    return data

def filename(phenny):
    name = phenny.nick + '-' + phenny.config.host + '.ethnologue.db'
    return os.path.join(os.path.expanduser('~/.phenny'), name)

def write_ethnologue_codes(phenny, raw=None):
    if raw is None or raw.admin:
        file = filename(phenny)
        data = scrape_ethnologue_codes()
        with open(file, 'w') as f:
            for k, v in data.items():
                f.write('{}${}\n'.format(k, v))
        phenny.ethno_data = data
        print('Ethnologue iso-639 code fetch successful')
        if raw:
            phenny.say('Ethnologue iso-639 code fetch successful')
    else:
        phenny.say('Only admins can execute that command!')

write_ethnologue_codes.name = 'write_ethnologue_codes'
write_ethnologue_codes.commands = ['write-ethno-codes']
write_ethnologue_codes.priority = 'low'

def read_ethnologue_codes(phenny, raw=None):
    file = filename(phenny)
    data = {}
    with open(file, 'r') as f:
        for line in f.readlines():
            code, name = line.split('$')
            data[code] = name
    phenny.ethno_data = data
    print('Ethnologue iso-639 database read successful')

def parse_num_speakers(s):
    hits = []
    for i in s.split(' '):
        if len(i) <= 3 or ',' in i:
            if i.replace(',', '').replace('.', '').isdigit():
                hits.append(int(i.replace(',', '').replace('.', '')))
    if 'ethnic population' in s.lower():
        return shorten_num(hits[0])
    return shorten_num(hits[-1])

def ethnologue(phenny, input):
    """.ethnologue <lg> - gives ethnologue info from partial language name or iso639"""
    raw = str(input.group(2)).lower()
    iso = []
    if len(raw) == 3 and raw in phenny.ethno_data:
        iso.append(raw)
    elif len(raw) > 3:
        for code, lang in phenny.ethno_data.items():
            if raw in lang.lower():
                iso.append(code)

    if len(iso) == 1:
        url = "http://www.ethnologue.com/language/" + iso[0]
        try:
            resp = urllib.request.urlopen(url).read()
        except HTTPError as e:
            phenny.say('Oh noes! Ethnologue responded with ', e)
            return
        h = html.document_fromstring(resp)

        name = h.get_element_by_id('page-title').text
        iso_code = h.find_class('field-name-language-iso-link-to-sil-org')[0].find('div/div/a').text
        where_spoken = h.find_class('field-name-a-language-of')[0].find('div/div/h2/a').text
        where_spoken_cont = h.find_class('field-name-field-region')
        if where_spoken_cont:
            where_spoken_cont = where_spoken_cont[0].find('div/div/p').text[:100]
            if len(where_spoken_cont) > 98:
                where_spoken_cont += '...'
            where_spoken += ', ' + where_spoken_cont
        if where_spoken[-1] != '.':
            where_spoken += '.'
        num_speakers_field = h.find_class('field-name-field-population')[0].find('div/div/p').text
        num_speakers = parse_num_speakers(num_speakers_field)
        language_status = h.find_class('field-name-language-status')[0].find('div/div/p').text.split('.')[0] + '.'

        response = "{} ({}): spoken in {} {} speakers. Status: {} Src: {}".format(
            name, iso_code, where_spoken, num_speakers, language_status, url)
    elif len(iso) > 1:
        did_you_mean = ['{} ({})'.format(i, phenny.ethno_data[i]) for i in iso if len(i) == 3]
        response = "Try .iso639 for better results. Did you mean: " + ', '.join(did_you_mean) + "?"
    else:
        response = "That ISO code wasn't found. (Hint: use .iso639 for better results)"

    phenny.say(response)

ethnologue.name = 'ethnologue'
ethnologue.commands = ['ethnologue', 'ethno', 'logue', 'lg', 'eth']
ethnologue.example = '.ethnologue khk'
ethnologue.priority = 'low'

def setup(phenny):
    file = filename(phenny)
    if os.path.exists(file):
        read_ethnologue_codes(phenny)
    else:
        write_ethnologue_codes(phenny)
