#!/usr/bin/env python

"""
hsg.py - Phenny module to find the HSG thread in the /co/ catalog.
Written by Tatpurusha, ported to phenny by !!c1Q
(It's not very pythonic, I'm sorry)
This is free and unencumbered software released into the public domain.
"""
import feedparser

global cmod
global hsglink

def findhsg():
    """fetches the rss, looks for some strings"""
    global cmod
    global hsglink

    RSS_URL="http://catalog.neet.tv/co/feed.rss"

    if 'cmod' in globals():
        catalog = feedparser.parse(RSS_URL, modified=cmod)
    else:
        catalog = feedparser.parse(RSS_URL)
    links = []
    cmod=catalog.modified
    #print catalog.status

    for item in catalog["items"]:
        if "homestuck general" in item["title"].lower():
            links.append(item["link"])

    for item in catalog["items"]:
        if "hsg" in item["title"].lower():
            links.append(item["link"])

    for item in catalog["items"]:
        if "homestuck general" in item["summary"].lower():
            links.append(item["link"])

    for item in catalog["items"]:
        if "homestuck" in item["title"].lower():
            links.append(item["link"])

    for item in catalog["items"]:
        if "homestuck" in item["summary"].lower():
            links.append(item["link"])

    if len(links) > 0:
        hsglink=links[0]
    else:
        links.append(hsglink)

    return links[0]

def hsg(phenny, input):
    phenny.say(findhsg())

hsg.commands = ['hsg']
hsg.priority = 'medium'

if __name__ == '__main__':
    print findhsg()
