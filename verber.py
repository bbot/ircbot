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

.addverb line of text :
  adds "line of text" to the text file

.delverb line of text :
  removes "line of text" from the text file

.findverb substring :
  shows up to three lines of text matching substring in text file

.verbreset :
  if owner or admin says this, resets the .verb timeout
  you should /msg this to the bot privately

.refreshwho #channel :
  forces the bot to fetch the userlist for that channel
  to make sure {3} in actions is populated.
  useful after you use .reload to live-update this module

This is free and unencumbered software released into the public domain.
"""

# TODO: text files still succumb to race conditions, move to dbm or sqlite
# TODO: add to action lines who submitted them, and when
# TODO: os.rename() fails in win32 because win32 filesystems SUCK
# unicode, man.  fuuuuuuuuck

# --

import codecs, os, random, re, time, tempfile

# .verb trigger , name of textile with one action per line, timeout in seconds
CONFIG = (
    ('verb', 'actions.txt', 180),
)


class VerberAfile(object):
    " the disk i/o (or db i/o) handler "
    # why did I made a class? so I can replace text files with db stuff someday
    def __init__(self, saycmd, afile, timeout=60 * 10, addcmd=None, delcmd=None, findcmd=None):
        self.afilename = afile
        self.saycmd = saycmd
        self.timeout = timeout
        self.addcmd = addcmd or 'add' + saycmd
        self.delcmd = delcmd or 'del' + saycmd
        self.findcmd = findcmd or 'find' + saycmd
        self.atime = 0

    def random_line(self):
        " exactly what it says on the tin "
        afile = codecs.open(self.afilename, 'rw', 'utf-8')
        line = next(afile)
        for num, aline in enumerate(afile):
            if aline.isspace() or aline[0] == '#':
                continue
            if random.randrange(num + 2):
                continue
            line = aline
        afile.close()
        return unicode(line)  # python2 still has str != unicode

    def append_to_file(self, newline):
        " exactly what it says on the tin "
        # Safe but not always reliable
        newline = newline.replace("\n", '').replace("\r", '').replace("\x00", '').strip()
        if len(newline) < 1:
            return False
        oldfile = codecs.open(self.afilename, 'rb', 'utf-8')
        fd, newfilename = tempfile.mkstemp()
        newfile = codecs.EncodedFile(os.fdopen(fd, 'wb'), 'utf-8')
        newfile.write(oldfile.read().encode('utf-8'))
        oldfile.close()
        newfile.write(newline.encode('utf-8'))
        newfile.write("\n")
        newfile.close()
        os.rename(newfilename, self.afilename)
        return True

    def delete_from_file(self, badline):
        " exactly what it says on the tin "
        # Safe but not always reliable
        badline = badline.replace("\n", '').replace("\r", '').replace("\x00", '')
        if len(badline) < 1:
            return False
        oldfile = codecs.open(self.afilename, 'rb', 'utf-8')
        fd, newfilename = tempfile.mkstemp()
        newfile = codecs.EncodedFile(os.fdopen(fd, 'wb'), 'utf-8')
        success = False
        for line in oldfile.readlines():
            if badline == line.strip():
                success = True
            else:
                newfile.write(line.encode('utf-8'))
        oldfile.close()
        newfile.close()
        if success:
            os.rename(newfilename, self.afilename)
        else:
            os.unlink(newfilename)
        return success

    def grep_in_file(self, needle):
        " exactly what it says on the tin "
        thefile = codecs.open(self.afilename, 'rb', 'utf-8')
        needle = needle.lower().strip()
        results = []
        for line in thefile:
            if needle in line.lower():
                results.append(line.strip())
        thefile.close()
        return results

# --

CLEANSE_RE = re.compile(r'[\s\r\n\x00]+', re.S)
BYSTANDERS = {}
ACTIONS = []
for acttup in CONFIG:
    print "... adding '.%s'" % acttup[0]
    ACTIONS.append(VerberAfile(acttup[0], acttup[1], acttup[2]))


def verber_onjoin(phenny, cmd_in):
    " because phenny doesn't already track channel info "
    chan = cmd_in
    who = cmd_in.nick
    if who == phenny.bot.nick:  # we're joining
        BYSTANDERS[chan] = set()
        phenny.write(('WHO', chan))  # server will respond with '352's
    else:
        BYSTANDERS.setdefault(chan, set())
        BYSTANDERS[chan].add(who)

verber_onjoin.event = 'JOIN'
verber_onjoin.rule = r'.'


def verber_on352(phenny, cmd_in):
    " because phenny doesn't already track channel info "
    chan = cmd_in.args[1]
    who = cmd_in.args[2]
    if not who[0].isalpha():  # status symbols like [@%~!]
        who = who[1:]
    if who == phenny.bot.nick:  # don't add myself to BYSTANDERS
        return
    BYSTANDERS[chan].add(who)

verber_on352.event = '352'
verber_on352.rule = r'.'


def verber_onpart(phenny, cmd_in):
    " because phenny doesn't already track channel info "
    chan = cmd_in.args[2]
    who = cmd_in.args[3]
    if who == phenny.bot.nick:
        # we're leaving
        del BYSTANDERS[chan]
    else:
        BYSTANDERS.setdefault(chan, set())
        BYSTANDERS[chan].discard(cmd_in.nick)

verber_onpart.event = 'PART'
verber_onjoin.rule = r'.'


def verber_timeout_reset(phenny, cmd_in):
    "kills the timeout on verber()"
    if not (cmd_in.admin or cmd_in.owner):
        return
    for i in ACTIONS:
        i.atime = 0
    phenny.msg(cmd_in.nick, "verber timeouts were reset")

verber_timeout_reset.commands = ['verbreset']
verber_timeout_reset.priority = 'low'


def verber_force_bystander_refresh(phenny, cmd_in):
    " force the bot to request WHO; good after '.reload verber' "
    if not (cmd_in.admin or cmd_in.owner):
        return
    chan = cmd_in.group(2)
    if not chan:
        chan = cmd_in.sender
    if not chan.startswith('#'):
        phenny.msg(cmd_in.nick, "invalid channel name '%s'" % chan)
        return
    phenny.msg(cmd_in.nick, "refreshing 'WHO' in %s" % chan)
    BYSTANDERS[chan] = set()
    phenny.write(('WHO', chan))  # server will respond with '352's

verber_force_bystander_refresh.commands = ['refreshwho']


def verber_addline(phenny, cmd_in):
    "Accept a new phrase/line to add to ACTION_FILE"
    action = None
    for i in ACTIONS:
        if i.addcmd == cmd_in.group(1):
            action = i
            break
    if action is None:
        raise Exception("assertion failure: addcmd %s not found" % repr(cmd_in.group(1)))
    if cmd_in.admin or cmd_in.owner:
        action.atime = 0
    if action.atime > time.time():
        phenny.msg(cmd_in.nick, "wait.")
        return
    newline = cmd_in.group(2)
    # need to sanitize for the use of str.format later
    if newline is None or newline == '' or newline.isspace():
        phenny.say(cmd_in.nick, ".%s some new phrase. substitutions: {0} invoker {1} arguments {2} channel {3} random name" % cmd_in.group(1))
        return
    newline = re.sub(r'[ \t\n]+', ' ', newline)
    newline = re.sub(r'{([456789]|\d\d+)}', '(\\1)', newline)
    if action.append_to_file(newline):
        phenny.say(cmd_in.nick, "%s: Added." % action.addcmd)
    else:
        phenny.say(cmd_in.nick, "%s: Couldn't add." % action.addcmd)
    action.atime += time.time() + 2  # throttling

verber_addline.commands = [j.addcmd for j in ACTIONS]
verber_addline.priority = 'low'
verber_addline.thread = True


def verber_delline(phenny, cmd_in):
    "Accept a line to be removed from ACTION_FILE"
    action = None
    for i in ACTIONS:
        if i.delcmd == cmd_in.group(1):
            action = i
            break
    if action is None:
        raise Exception("assertion failure: delcmd %s not found" % repr(cmd_in.group(1)))
    if not (cmd_in.admin or cmd_in.owner):
        # only people we trust can grep action lines
        return
    badline = cmd_in.group(2)
    if badline is None or badline == '' or badline.isspace():
        phenny.say(".%s needs the phrase you want removed" % action.delcmd)
        return
    if action.delete_from_file(badline):
        phenny.say("%s: Removed." % action.delcmd)
    else:
        phenny.say("%s: Couldn't remove." % action.delcmd)

verber_delline.commands = [j.delcmd for j in ACTIONS]
verber_delline.priority = 'low'
verber_delline.thread = True


def verber_findline(phenny, cmd_in):
    "grep ACTION_FILE, privmsg results"
    action = None
    for i in ACTIONS:
        if i.findcmd == cmd_in.group(1):
            action = i
            break
    if action is None:
        raise Exception("assertion failure: findcmd %s not found" % repr(cmd_in.group(1)))
    if not (cmd_in.admin or cmd_in.owner):
        # only people we trust can grep action lines
        return
    needle = cmd_in.group(2).strip()
    if needle == '':
        phenny.msg(cmd_in.nick, ".%s something needs the phrase you want removed" % action.findcmd)
        return
    found = action.grep_in_file(needle)
    if len(found) > 0:
        for i in found[:3]:
            phenny.msg(cmd_in.nick, "%s: \"%s\"" % (action.findcmd, i))
    else:
        phenny.msg(cmd_in.nick, "%s: no matching phrases found" % action.findcmd)

verber_findline.commands = [j.findcmd for j in ACTIONS]
verber_findline.priority = 'low'
verber_findline.thread = True


def verber_sayline(phenny, cmd_in):
    "Utter a random line from text file with fill-in-the-blanks"
    action = None
    for i in ACTIONS:
        if i.saycmd == cmd_in.group(1):
            action = i
            break
    if action is None:
        raise Exception("assertion failure: findcmd %s not found" % repr(cmd_in.group(1)))
    if cmd_in.admin or cmd_in.owner:
        action.timeout = 0  # collapse the timeout
    if action.atime > time.time():  # if the timeout hasn't expired yet...
        phenny.msg(cmd_in.nick, 'Wait %d seconds.' % (action.atime - time.time()))
        return
    chan = cmd_in.sender
    if not chan.startswith('#'):  # if this is not a real channel...
        return  # ... nah.
    nick = cmd_in.nick
    victim = cmd_in.group(2)
    if not victim:
        victim = 'nobody'
    if victim == phenny.bot.nick:
        action.atime += action.timeout
        phenny.say('No.')  # refuse to autoverbate
        return
    try:
        bystanders = list(BYSTANDERS[chan],)
        bystanders.remove(phenny.bot.nick)
        bystanders.remove(nick)  # don't use requester's own nick ...
        bystander = random.choice(bystanders)
    except (KeyError, IndexError):
        bystander = nick  # ... unless requester is all alone
    line = action.random_line().format(nick, victim, chan, bystander)
    action.atime = time.time() + action.timeout
    phenny.say('\x01ACTION %s\x01' % line)  # emote

verber_sayline.commands = [j.saycmd for j in ACTIONS]
verber_sayline.priority = 'low'
verber_sayline.thread = True
