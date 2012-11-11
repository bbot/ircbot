How to make a phenny module, the crash course:
----------------------------------------------
### step 1a:
drink from ye flask

### step 1b:
open ye favourite python code editore

### step 3:
New text file in the phenny 'modules' directory. This will be a python
module, so put .py on the end of the filename. Phenny loads all the
modules in a directory on launch, and tries to make every item in
dir(module) into a hook, but only the ones that are callable and have
either a .rule or .commands attribute actually get launched

### step 4:
Define a function to receive two parameters: phenny 'self' and a
message data object.  Don't call the second param 'input' like in
the phenny examples, because that's a reserved word in Python.  Derp.

`def fortune_cookie(phenny, data):`

The 'phenny' parameter is the bot's "self", an instance of bot.Phenny,
a subclass of irc.Bot, subclass of asynchat.aync\_chat .  Useful
attributes and methods I discovered are:

 - **.origin** : irc.Origin instance, it is exactly the same as
  what is passed as data.origin, which you should use instead.
 - **.reply(mesg)** : sends a privmsg back to the person that
  prompted this function to launch.
 - **.say(mesg)** : sends a privmsg back to the channel of the message
  that prompted this function to launch.
 - **.write(code, param1, ...)** : send a raw IRC message
  (ie. phenny.write('JOIN', channelname, key) )
 - **.notice(target,mesg)** : same as .write('NOTICE',target,mesg)
 - **.msg(target,mesg)** : same as .write('PRIVMSG',target,mesg)
  (ie. phenny.msg('NickServ','IDENTIFY %s' % phenny.config.nickservpass) )
 - **.config** : a dict() of the bot's configuration settings.
 - **.error(irc.Origin(??))** : too messy to use; supposed to send
  a callstack to a human or logfile when an exception is thrown.

This is what I managed to figure out about the 'data' parameter.
It is supposed to bear info about an IRC message like this:
`:nick!user@hostname PRIVMSG target :alpha beta etc`

 - **.origin.nick** : the 'nick' part of :nick!user@hostname
 - **.origin.user** : the 'user' part of :nick!user@hostname
 - **.origin.host** : the 'hostname' part of :nick!user@hostname
 - **.event** : the second part of the IRC message (ie. 'PRIVMSG',
  'NOTICE') I don't know if you get the text or the numer code, or just
  whatever the server used.
 - **.bytes** : I think this is the event payload after the second ':'
  mark ('alpha beta etc' in the example)

 - **.sender** : EITHER: if the message was sent to the bot, this is
  the same as .origin.nick , but if it was sent to channel, it will
  have the '#target' string including the '#'.
  check .sender[0] == '#' to see which it is at runtime
 - **.nick** : identical to .origin.nick
 - **.match** : a MatchObject returned from the regexp string assigned to
  this command or rule.  See below.
 - **.group** : identical to .match.group
 - **.groups** : identical to .match.groups
 - **.args** : I don't know, it is never used by known phenny modules.
 - **.admin** : True if .nick in phenny.config.admins *do not trust this*
 - **.owner** : True if .nick == phenny.config.owner *do not trust this*

The last two should never be used, because .nick ignores hostmask,
so someone could '/nick ceequof' during a session and Do Bad Things™.

I have no idea what the function's return value should be.  I would assume
that anything other than `None` or `False` would stop Phenny from handing
the data to any other hooked-in functions, but

### step 5:

To make a function launch for every message the bots that matches a regular
expression, add these attributes to the function.  The attribute rule
or the attribute commands must be present (and both can be present,
see below).  The rest are optional.

 - **.rule = str()** : a string to be passed to re.compile(), used
  for matching against the payload of every event (ie. after the second
  ':' mark).  If it matches, launch the function and pass the MatchObject
  as data.match .  the string can have '$nick' in it which will be converted
  to the bot's nickname at load time; changing the bot's nick later will
  not update this rule.
 - **.rule = (str(),str())** : identical to .rule = str()+str() but the
  '$nick' substitution only happens in the first string.
 - **.rule = (list(),str())** : a way to have multiple commands call the
  same function.  ie. `.rule = (['love','hate'],r'my \S+')` would be like
  .rule = r'eat my \S+' and .rule = r'suck my \S+' at the same time.
  There is no '$nick' substitution.
 - **.rule = (str(),list(),str())** : like the above, but now
  `.rule = ('kanaya',['loves','hates'],'\S+')` becomes .rule = r'kanaya
  loves \S+' and .rule = 'kanaya hates \S+'.  The '$nick' substitution
  is only done for the first str().
 - **.commands = list()** : identical to
  .rule = ('^'+phenny.config.prefix,list(),r'(.\*)?')

 - **.event** : which events to check .rule against.  Defaults to 'PRIVMSG'.
 - **.priority** : can be 'high', 'medium', or 'low'.  Defaults to 'medium'.
  Functions with 'high' priority are checked first, then 'medium', then 'low'.
  Note well that a successful match will not stop checking for other
  matches and possibly launching other functions.
 - **.thread** : whether to give this function to a thread of its own
  for processing.  Defaults to True.
 - **.name** : not sure. defaults to .\_\_name\_\_
 - **.example** : not sure. defaults to .\_\_doc\_\_

### Example:

    import random, time

    COOLDOWN = 300
    NAMES = """Aradia Tavros Sollux Nepeta Karkat Kanaya
               Terezi Vriska Equius Gamzee Eridan Feferi
               John Rose Dave Jade Jane Roxy Dirk Jake
            """.split()

    def _make_namepair(name_l=None):
      random.shuffle(NAMES)
      if name_l:
        name_l = name_l.title()
        if not name_l in NAMES:
          name_l = None
      if not name_l:
        name_l = NAMES[0]
        name_r = NAMES[1]
      elif name_l == NAMES[0]:
        name_r = NAMES[1]
      else:
        name_r = NAMES[0]
      return (name_l, name_r)

    ATIME = 0
    def crackship(phenny, data):
      " utters a nonsense romance pairing of two characters "
      global ATIME
      now = time.time()
      if ATIME + COOLDOWN < now :
        namepair = _make_namepair(data.match.group(2))
        phenny.say("I ship %s with %s" % namepair)
        ATIME = now
        return True

    crackship.commands = ['ship','crackship']
    crackship.rule = r'you ship (\S+(?:\s+\S+)) (?:and|with) \S+'

    if __name__ == '__main__':
      " so we can test this without importing to phenny "
      for i in range(6):
        namepair = _make_namepair()
        print "I ship %s with %s" % namepair
      namepair = _make_namepair('John')
      print "(John) I ship %s with %s" % namepair
      namepair = _make_namepair('Karkat')
      print "(Karkat) I ship %s with %s" % namepair

