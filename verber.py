#!/usr/bin/env python

"""
verber.py - Performs actions

Reads a line from actions.txt, replaces {1} with the target, and prints it in the channel as an emote.

Includes a 10 minute timeout to prevent abuse. Requires the phenny.action() method from PinkiePyBot: 
https://github.com/JordanKinsley/PinkiePyBot/blob/master/irc.py#L202

This is free and unencumbered software released into the public domain.
"""

import random, time

timeout = 1

def random_line(afile):
    line = next(afile)
    for num, aline in enumerate(afile):
        if random.randrange(num + 2): 
            continue
        line = aline
    return line

def verber(phenny, input):
    global timeout #This accesses the timeout variable declared outside of local scope.
                   #This number actually does persist between invocations. You wouldn't think so, but it does.
    nick = input.nick
    now = time.time()
    if (timeout < now):                 #if the timeout is in the past...
        timeout = (now + 10 * 60)       #...add ten minutes and perform the action
        phenny.action(input.sender, random_line(open('actions.txt')).format(nick, input.group(2)))
        #The name of the person who invoked the bot is {0} in the template, and the target is {1}
    else:
        return #otherwise do nothing

verber.commands = ['verb']
verber.priority = 'low'
