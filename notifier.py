#!/usr/bin/env python

"""
notifier.py - Phenny module to check if Homestuck's been updated
Written by Mozai, ported to Phenny by !!c1Q
This is free and unencumbered software released into the public domain.
"""

import httplib, time, rfc822, socket

def notifier(phenny, input):
    """
    main loop
    
    sleeps for three hours after an update since you rarely
    see two updates right after each other
    """
    time.sleep(5)
    while True:
        if hs_update(recent=180):
            phenny.say("=========================================")
            phenny.say("UPDATE UPDATE UPDATE UPDATE UPDATE UPDATE")
            phenny.say("      http://mspaintadventures.com/")
            phenny.say("=========================================")
            time.sleep(60 * 60 * 3)
        else:
            time.sleep(20)
notifier.commands = ['notify']
notifier.priority = 'medium'

def hs_update(host='mspaintadventures.com', path='/rss/rss.xml', recent=180):
    """checks how recently the RSS feed's been updated"""
    try:
        connect = httplib.HTTPConnection(host, timeout=2)
        connect.request("HEAD", path)
        lastmodified = connect.getresponse().getheader('Last-Modified')
        if lastmodified:
            lastmodified = time.mktime(rfc822.parsedate(lastmodified))
            if ((time.mktime(time.gmtime()) - recent) < lastmodified):
                return True
            return False
    except socket.timeout:
        print "Timeout", time.asctime()

if __name__ == '__main__':
    while True:
        if hs_update(recent=300):
            print "Homestuck updated in the past 5 minutes (300 seconds)"
        else:
            print "Homestuck hasn't updated in the last 5 minutes; calm down."
            time.sleep(1)
