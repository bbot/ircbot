#!/usr/bin/env python
"""
verber.py - Performs emote from a list on demand

.verb [target] :
  Reads a line from ./actions.txt, replaces {#}, and emotes it
  {0}: name of the invoker
  {1}: string after the invoking command
  {2}: channel it was invoked in
  {3}: random name of person in that channel
  Includes a 10 minute timeout to prevent abuse.

.verbreset :
  if owner or admin says this, resets the .verb timeout
  you should /msg this to the bot privately

.refreshwho #channel :
  forces the bot to fetch the userlist for that channel
  to make sure {3} in actions is populated.
  useful after you use .reload to live-update this module

This is free and unencumbered software released into the public domain.
"""

# TODO: text files are not thread-safe, move to dbm or sqlite
# TODO: add to action lines who submitted them, and when
import random, re, time

TIMEOUT_DELAY = 60 * 10  # ten minutes
ACTION_FILE = './actions.txt'


def random_line(afile):
    " return random line of text from file object or filename "
    if isinstance(afile, str):
        afile = open(afile, 'r')
    if not isinstance(afile, file):
        raise TypeError('need file or filename')
    line = next(afile)
    for num, aline in enumerate(afile):
        if aline.isspace() or aline[0] == '#':
            continue
        if random.randrange(num + 2):
            continue
        line = aline
    afile.close()
    return unicode(line)  # python2 still has str != unicode


def verber_onjoin(phenny, cmd_in):
    " because phenny doesn't already track channel info "
    chan = cmd_in
    self = phenny.variables['verber']
    who = cmd_in.nick
    if who == phenny.bot.nick:  # we're joining
        self.bystanders[chan] = set()
        phenny.write(('WHO', chan))  # server will respond with '352's
    else:
        self.bystanders.setdefault(chan, set())
        self.bystanders[chan].add(who)

verber_onjoin.event = 'JOIN'
verber_onjoin.rule = r'.'


def verber_on352(phenny, cmd_in):
    " because phenny doesn't already track channel info "
    self = phenny.variables['verber']
    chan = cmd_in.args[1]
    who = cmd_in.args[2]
    if not who[0].isalpha():  # status symbols like [@%~!]
        who = who[1:]
    if who == phenny.bot.nick:  # don't add myself to bystanders
        return
    self.bystanders[chan].add(who)

verber_on352.event = '352'
verber_on352.rule = r'.'


def verber_onpart(phenny, cmd_in):
    " because phenny doesn't already track channel info "
    self = phenny.variables['verber']
    chan = cmd_in.args[2]
    who = cmd_in.args[3]
    if who == phenny.bot.nick:
        # we're leaving
        del self.bystanders[chan]
    else:
        self.bystanders.setdefault(chan, set())
        self.bystanders[chan].discard(cmd_in.nick)

verber_onpart.event = 'PART'
verber_onjoin.rule = r'.'


def verber_timeout_reset(phenny, cmd_in):
    "kills the timeout on verber()"
    self = phenny.variables['verber']
    if cmd_in.admin or cmd_in.owner:  # this is not safe
        self.timeout = 0
        phenny.say("timeout reset for .verb")

verber_timeout_reset.commands = ['verbreset']
verber_timeout_reset.priority = 'low'


def verber_force_bystander_refresh(phenny, cmd_in):
    " force the bot to request WHO; good after '.reload verber' "
    self = phenny.variables['verber']
    chan = cmd_in.group(2)
    if not chan.startswith('#'):
        phenny.say("invalid channel name '%s'" % chan)
        return
    if cmd_in.admin or cmd_in.owner:  # this is not safe
        phenny.say("refreshing 'WHO' in %s" % chan)
        self.bystanders[chan] = set()
        phenny.write(('WHO', chan))  # server will respond with '352's

verber_force_bystander_refresh.commands = ['refreshwho']


def verber_addline(phenny, cmd_in):
    "Accept a new phrase/line to add to ACTION_FILE"
    self = phenny.bot.variables['verber_addline']
    # nick = cmd_in.nick
    # if not (cmd_in.admin or cmd_in.owner):
    #     # only people we trust can add new action lines
    #     return
    now = time.time()
    if self.timeout > now:  # if the timeout isn't here yet...
        return  # ... do nothing
    newline = cmd_in.group(2)
    # need to sanitize for the use of str.format later
    newline = re.sub(r'{([456789]|\d\d+)}', '(\\1)', newline)
    newline = re.sub(r'[ \t\n]+', ' ', newline)
    if newline == '' or newline.isspace():
        phenny.say(".addverb some new phrase. substitutions: {0} invoker {1} arguments {2} channel {3} random name")
        self.timeout = (now + 10)  # wait ten seconds before responding
    else:
        with open(ACTION_FILE, 'a') as outfile:
            outfile.write("\n")
            outfile.write(newline)
        phenny.say("New verbphrase added.")
        self.timeout = (now + TIMEOUT_DELAY)  # wait X seconds
    return

verber_addline.commands = ['addverb']
verber_addline.thread = False  # appending to text file is not thread-safe
verber_addline.timeout = 0


def verber(phenny, cmd_in):
    "Utter a random line from text file with fill-in-the-blanks"
    self = phenny.bot.variables['verber']
    nick = cmd_in.nick
    victim = cmd_in.group(2)
    if not victim:
        victim = 'nobody'
    chan = cmd_in.sender
    if not chan.startswith('#'):  # if this is not a real channel...
        return  # ... nah.
    try:
        bystanders = set(self.bystanders[chan])
        bystanders.discard(nick)  # don't use requester...
        bystander = random.choice(list(self.bystanders[chan],))
    except (KeyError, IndexError):
        bystander = nick  # ... unless requester is all alone
    if victim == phenny.bot.nick:
        phenny.say('No.')
    now = time.time()
    if self.timeout < now:  # if the timeout is in the past...
        self.timeout = (now + TIMEOUT_DELAY)  # ...increment timeout
        line = random_line(ACTION_FILE).format(nick, victim, chan, bystander)
        phenny.say('\x01ACTION %s\x01' % line)  # this is /me
    # elif (cmd_in.admin or cmd_in.owner):  # this is not safe
        # self.timeout = (now + TIMEOUT_DELAY)  # ...increment timeout
        # line = random_line(ACTION_FILE).format(nick, victim, chan, bystander)
        # phenny.action(chan, line)
    else:
        # phenny.say(cmd_in.nick, 'please wait %d seconds' % (self.timeout - now))
        return

verber.commands = ['verb']
verber.priority = 'low'
verber.thread = True
verber.timeout = 0
verber.bystanders = {}
