#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Your task is to use the iterative parsing to process the map file and
find out not only what tags are there, but also how many, to get the
feeling on how much of which data you can expect to have in the map.
Fill out the count_tags function. It should return a dictionary with the 
tag name as the key and number of times this tag can be encountered in 
the map as value.

Note that your code will be tested with a different data file than the 'example.osm'
"""
import xml.etree.cElementTree as ET
import pprint
from collections import defaultdict
import re

lower = re.compile(r'^([a-z_])*$')
lower_colon = re.compile(r'^([a-z_])*:([a-z_])*$')
problemchars = re.compile(r'[=+/&<>;\'"?%#$@,. \t\r\n]')
house_numbers_re = re.compile(r'\d*[a-zA-Z]?')
street_number_re = re.compile(r'\d*$')
num_search_re = re.compile(r'\d')

def count_tags(filename):
    housenums = defaultdict(int)
    #iterparse returns iterator of (event, elem) pairs
    context = ET.iterparse(filename)
    #loop through context interator
    for event, elem in context:
        if elem.tag == "tag" and elem.get("k") == "addr:housenumber":
            housenumber = elem.get("v")
            try: 
                float(housenumber)
            except ValueError:
                housenums[housenumber] += 1
                value = num_search_re.match(housenumber)
                if value:
                    unit = house_numbers_re.match(housenumber)
                    street = street_number_re.search(housenumber)
                    if unit:
                        print("unit", unit.group())
                    if street:
                        print("street", street.group())
    return housenums

def test():

    tags = count_tags('example.osm')
    pprint.pprint(tags)
    assert tags == {'bounds': 1,
                     'member': 3,
                     'nd': 4,
                     'node': 20,
                     'osm': 1,
                     'relation': 1,
                     'tag': 7,
                     'way': 1}

    

if __name__ == "__main__":
    log = open('housenumslog.txt', 'w')
    housenums = count_tags('regina_canada.osm')
    pprint.pprint(housenums, stream = log)