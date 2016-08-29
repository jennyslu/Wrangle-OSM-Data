#!/usr/bin/env python
# -*- coding: utf-8 -*-
import xml.etree.cElementTree as ET
import pprint
import re
import codecs
import json
"""
Your task is to wrangle the data and transform the shape of the data
into the model we mentioned earlier. The output should be a list of dictionaries
that look like this:

{
"id": "2406124091",
"type: "node",
"visible":"true",
"created": {
          "version":"2",
          "changeset":"17206049",
          "timestamp":"2013-08-03T16:43:42Z",
          "user":"linuxUser16",
          "uid":"1219059"
        },
"pos": [41.9757030, -87.6921867],
"address": {
          "housenumber": "5157",
          "postcode": "60625",
          "street": "North Lincoln Ave"
        },
"amenity": "restaurant",
"cuisine": "mexican",
"name": "La Cabana De Don Luis",
"phone": "1 (773)-271-5176"
}

You have to complete the function 'shape_element'.
We have provided a function that will parse the map file, and call the function with the element
as an argument. You should return a dictionary, containing the shaped data for that element.
We have also provided a way to save the data in a file, so that you could use
mongoimport later on to import the shaped data into MongoDB. 

Note that in this exercise we do not use the 'update street name' procedures
you worked on in the previous exercise. If you are using this code in your final
project, you are strongly encouraged to use the code from previous exercise to 
update the street names before you save them to JSON. 

In particular the following things should be done:
- you should process only 2 types of top level tags: "node" and "way"
- all attributes of "node" and "way" should be turned into regular key/value pairs, except:
    - attributes in the CREATED array should be added under a key "created"
    - attributes for latitude and longitude should be added to a "pos" array,
      for use in geospacial indexing. Make sure the values inside "pos" array are floats
      and not strings. 
- if the second level tag "k" value contains problematic characters, it should be ignored
- if the second level tag "k" value starts with "addr:", it should be added to a dictionary "address"
- if the second level tag "k" value does not start with "addr:", but contains ":", you can
  process it in a way that you feel is best. For example, you might split it into a two-level
  dictionary like with "addr:", or otherwise convert the ":" to create a valid key.
- if there is a second ":" that separates the type/direction of a street,
  the tag should be ignored, for example:

<tag k="addr:housenumber" v="5158"/>
<tag k="addr:street" v="North Lincoln Avenue"/>
<tag k="addr:street:name" v="Lincoln"/>
<tag k="addr:street:prefix" v="North"/>
<tag k="addr:street:type" v="Avenue"/>
<tag k="amenity" v="pharmacy"/>

  should be turned into:

{...
"address": {
    "housenumber": 5158,
    "street": "North Lincoln Avenue"
}
"amenity": "pharmacy",
...
}

- for "way" specifically:

  <nd ref="305896090"/>
  <nd ref="1719825889"/>

should be turned into
"node_refs": ["305896090", "1719825889"]
"""

#regex expressions for three different tag types
lower = re.compile(r'^([a-z_])*$')
lower_colon = re.compile(r'^([a-z_])*:([a-z_])*$')
problemchars = re.compile(r'[=+/&<>;\'"?%#$@,. \t\r\n]')

#regex for finding street type (string at end with optional .)
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)

#regex for unit number (all numbers at beginning of string with optional letter at end)
house_numbers_re = re.compile(r'\d*[a-zA-Z]?')
#if house number string contains house number it is group of numbers at end
street_number_re = re.compile(r'\d*$')
#find if string contains any numbers
num_search_re = re.compile(r'\d')


def shape_element(element):
    node = {}
    #create: {...} keys have values that are all node/way attributes
    create = ["version", "changeset", "timestamp", "user", "uid"]
    createdict = {}
    addr = {}
    
    #only process nodes and ways
    if element.tag == "node" or element.tag == "way": 
        #print(element.tag)
        
        #create lat, lon array for node
        if element.tag == "node":
            node["pos"] = [float(element.get("lat")), float(element.get("lon"))]
        #create list of nd reference values for way
        elif element.tag == "way":
            ref = []
            for nd in element.findall("nd"):
                ref.append(nd.get("ref"))
            node["node_refs"] = ref

        node["type"] = element.tag
        node["id"] = element.get("id")
        #this OSM file does not have "visible attribute"
        #node["visible"] = element.get("visible")

        #furnish create dict
        for key in create:
            createdict[key] = element.get(key)
        node["created"] = createdict
        
        #find tag node that is second child of the parent
        second = element.find(".//tag[2]")
        #if node/way has tag nodes then:
        if second != None:
            for tag in element.findall("tag"):
                secondkey = second.get("k")
                #skip problem character tags (although none exist in Regina)
                if problemchars.search(secondkey):
                    pass
                elif tag.get("k").startswith("addr:"):
                    addrkey = tag.get("k").replace("addr:", "")
                    addrvalue = tag.get("v")
                    #fix street type value problems identified by audit.py
                    if addrkey == "street":
                        addr[addrkey] = audit_street_type(addrvalue)
                    #all postcode values previously confirmed to be valid
                    elif addrkey == "postcode":
                        addr[addrkey] = addrvalue
                    #fix house number value problems identified by housenumber.py
                    elif addrkey == "housenumber":
                        try: 
                            float(addrvalue)
                            addr[addrkey] = addrvalue
                        except ValueError:
                            #value must begin with number to eliminate invalid strings found from housenumber.py
                            value = num_search_re.match(addrvalue)
                            if value:
                                unitvalue, housevalue = update_housenum(addrvalue)
                                addr["unit"] = unitvalue
                                addr["housenumber"] = housevalue
                            #if value is a string set to "name" instead of housenumber
                            else:
                                node["name"] = addrvalue
                    elif addrkey == "unit":
                        addr[addrkey] = addrvalue
                    #ignore all other address values (eg. city, country, province, etc.)
                    else:
                        pass
                    node["address"] = addr
                #ignore all "other" tags found in tagparser.py
                elif not(lower.match(tag.get("k"))) and not(lower_colon.match(tag.get("k"))):
                    pass
                #process other colon tags into lower case tags with _
                #also process other lower case tags
                else:
                    nodekey = tag.get("k")
                    nodekey = nodekey.replace(":", "_")
                    node[nodekey] = tag.get("v")
        return node

#~~~STREET TYPE CORRECTION~~~
#this list from audit.py
expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road", 
            "Trail", "Parkway", "Commons", "Bay", "Crescent", "Estates", "Gate", "Glen", "Greens", 
            "Grove", "Heights", "Highlands", "Mews", "Point", "Way", "Centre", "Circle", "Cove",
            "Loop", "Meadow", "Ridge", "Terrace", "E", "N", "Highway"]
#this dict from audit.py
mapping = { "St": "Street",
            "St.": "Street",
            "Ave": "Avenue",
            "Rd.": "Road",
            "BOULEVARD": "Boulevard",
            "Dr": "Drive",
            "GROVE": "Grove",
            "Rd": "Road",
            "North": "N"}
#search for street type and replace with correction from mapping dict if it is not in expected list
#values for mapping and expected found from audit.py
def audit_street_type(street_name):
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            street_name = update_name(street_name, mapping).title()
    return street_name
#function to update wrong street type with correction
def update_name(name, mapping):
    m = street_type_re.search(name)
    wrong_street = m.group()
    name = name.replace(wrong_street, mapping[wrong_street], 1)
    return name

'''
~~~HOUSE NUMBER CORRECTION~~~
this function returns unit number and house number
unit number is first set of numbers (with optional letter)
house number is second set of numbers only (if it exists)
empty strings returned if there is no house number (often the case)
'''
def update_housenum(housenumber):
    unitvalue = ""
    streetvalue = ""     
    #take first group of numbers with optional letter at end for unit number
    unit = house_numbers_re.match(housenumber)
    #take last set of numbers as street number (typically doesn't exist)
    street = street_number_re.search(housenumber)
    if unit:
        unitvalue = unit.group()
    if street:
        streetvalue = street.group()   
    return(unitvalue, streetvalue)

'''
#this function does not return a valid json document as json documents are not enclosed in list
#and are separated by new lines instead of commas
#therefore json.loads and insert cannot be used; mongoimport will be used instead to upload
'''
def process_map(file_in, pretty = False):
    # You do not need to change this file
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
        for _, element in ET.iterparse(file_in):
            el = shape_element(element)
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=2)+"\n")
                else:
                    fo.write(json.dumps(el) + "\n")
    return data

def test():
    # NOTE: if you are running this code on your computer, with a larger dataset, 
    # call the process_map procedure with pretty=False. The pretty=True option adds 
    # additional spaces to the output, making it significantly larger.
    data = process_map('example.osm', True)
    #pprint.pprint(data)
    
    correct_first_elem = {
        "id": "261114295", 
        "visible": "true", 
        "type": "node", 
        "pos": [41.9730791, -87.6866303], 
        "created": {
            "changeset": "11129782", 
            "user": "bbmiller", 
            "version": "7", 
            "uid": "451048", 
            "timestamp": "2012-03-28T18:31:23Z"
        }
    }
    assert data[0] == correct_first_elem
    assert data[-1]["address"] == {
                                    "street": "West Lexington St.", 
                                    "housenumber": "1412"
                                      }
    assert data[-1]["node_refs"] == [ "2199822281", "2199822390",  "2199822392", "2199822369", 
                                    "2199822370", "2199822284", "2199822281"]

if __name__ == "__main__":
    process_map('regina_canada.osm',False)