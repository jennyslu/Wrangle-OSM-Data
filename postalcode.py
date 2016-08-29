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


def count_tags(filename):
    postal_count = defaultdict(int)
    #iterparse returns iterator of (event, elem) pairs
    context = ET.iterparse(filename)
    #loop through context interator
    for event, elem in context:
        if elem.tag == "tag" and elem.get("k") == "addr:postcode":
            postalcode = elem.get("v")
            if postalcode.startswith("S4"):
                postal_count[postalcode[2]] += 1
    return postal_count

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
    postalcodes = count_tags('regina_canada.osm')
    pprint.pprint(postalcodes)