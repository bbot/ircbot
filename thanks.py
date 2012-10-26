#!/usr/bin/env python

"""
hsg.py - Says no problem when you do .thanks.

Not that it matters, but this is free and unencumbered software released into the public domain.
"""

def thanks(phenny, input):
    phenny.say("No problem.")

thanks.commands = ['thanks']
thanks.priority = 'medium'
