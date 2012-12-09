How to make a phenny module, the crash course:
==============================================

## step 1a ##
get ye flask. drink from ye flask

## step 1b ##
open ye favourite python code editore

## step 3 ##
New text file in the phenny 'modules' directory. This will be a python
module, so put .py on the end of the filename. Phenny loads all the
modules in a directory on launch, and tries to make every item in
dir(module) into a hook, but only the ones that are callable and have
either a .rule or .commands attribute actually get launched

## step 4 ##
Define a function to receive two parameters: the bot's isntance
wrapped in another class, and information about the message that
triggered the call of this function.  They are called 'phenny' and
'input' in the phenny documentation, but those aren't good names.
('input' itself is already the name of a callable in irc.Phenny, and
also a callable in python's \_\_builtin\_\_.  Double-derp.)

`def fortune_cookie(phenny, cmd_in):`

### phenny parameter ###
The '**phenny**' parameter is an instance of PhennyWrapper, which doesn't
show up with introspection because the class is defined inside a function,
despite being used outside that function.  The bot's "self" is accessable
as phenny.bot, and it is an instance of bot.Phenny .  Useful attributes
of phenny.bot are:

- **.bot.write(args, text=None)** : send a raw IRC message. 'args' is a tuple
  for the IRC command and parameters, 'text' is the trailing parameter.
  examples: 
  - .bot.write(('NICK',"Caliborn"))  
  - .bot.write(('KICK',"Caliope"),"Stop with the role-playing")
- **.bot.msg(destination, text)** : safer than using .write() for 
  PRIVMSG as it includes some unicode cooking and message-throttling.
  - .bot.msg('#cantown',"Elections are starting, don't forget to vote!")
- **.say(text)** : same as .msg() but infers the destination is the
  same as that of the triggering privmsg (if is is a #channel) or
  the nick of the sender of the privmsg (if destination was the bot).
  - .say("ALL OF YOU ARE A BUNCH OF WIGGLERS")
- **.reply(text)** : same as .msg() but prepends the nick of whoever
  sent the triggering message at the start 
  - .reply("i kn0w what im d0ing")
- **.bot.error(origin)** : Used in try/except blocks to report when 
  an exception was thrown. The same as .say(repr(exception))
- **.bot.log(mesg)** : this is identical to 
  `sys.stderr.write('log: %s\n')`
- **.bot.config** : each of the settings written in
  ~/.phenny/default.py are attributes of phenny.config (ie.
  phenny.config.prefix)
- **.bot.stats** : dictionary tallying how often phenny modules are 
  used and by whom.  key is (module.name, source), value is int.
- **.bot.nick** : bot's IRC nick; usueally used  to notice when
  someone's addressing the bot by name.
- **.bot.channels** : list of channels the bot listens to
- **.bot.stack** : list of (timestamp, text) tuples of what the bot
  has said recently. Used by Phenny for output throttling and detecting
  message duplicates.
- **.bot.variables** : dict() of 'name':callable for each of the 
  functions loaded from phenny modules.
- **.bot.doc** : dictionary of 'command':('descrip','example') help 
  strings for commands.  Only used by the 'info' phenny module.

If you included the phenny module 'setup' (which provides some things
that really aught to be in the core instead), phenny.bot will also have
an attribute `.data` which appears to be an empty dict.  This maybe 
meant for use by modules to store persistent data between calls, but
there is a safer and more reliable way explained at the end of step 5.

### cmd_in parameter ###
It's a subclass of unicode(), but the real class def is another one
defined inside a class method so introspection doesn't work.

First, a crash course in IRC messages.  They usually look like this:

`:nick!user@hostname PRIVMSG target :trailing alpha beta etc`

In IRC, the first part is supposed to be the source of a message 
being relayed.  If it is empty (doesn't start with ':', or is only 
':') then the client assumes the server is the source, and vice 
versa.  The words after are called parameters, separated by spaces.  
The first parameter is also called the IRC 'event'.  A parameter that
start with ':' is considered the last parameter, called the 'trailing'
parameter, and includes everything between ':' and the '\r\n' that
ends every IRC message.

- **.\_\_repr\_\_** : the trailing parameter of the message.
- **.event** : the the first parameter (ie. 'PRIVMSG', 'NOTICE')
- **.bytes** : This is the trailing parameter without any encoding into
  utf-8, iso-8859-1, or that Microsoft gnarly codepage for en-US. 
  You're better off using cmd_in as a string in almost all cases.
- **.sender** : EITHER: if the message was sent to the bot, this is
  the same as .origin.nick , but if it was sent to channel, it will
  have the '#target' string including the '#'.
  check .sender[0] == '#' to see which it is at runtime.
  You're better off using phenny.say() anyways.
- **.nick** : the nick part (before the !) of the message.
- **.match** : the result of the re.match() that triggered this function
- **.group()** : same as .match.group()
- **.groups()** : same as .match.groups()
- **.args** : A tuple of all the IRC message parameters except
  the first and trailing
- **.admin** : True if .nick in phenny.config.admins *do not trust this*
- **.owner** : True if .nick == phenny.config.owner *do not trust this*

The last two should never be used, because .nick ignores hostmask,
so someone could '/nick ceequof' during a session to look like the
bot's owner and use it to Do Bad Things™.

The function's return value is discarded; don't bother making one.

## step 5 ##

To make a function launch for every message the bots that matches a 
regular expression, add these attributes to the function.  The 
attribute rule or the attribute commands must be present (and both 
can be present, see below).  The rest are optional.

Note: a module's "rule" is compiled with re.compile(), and later 
used by the bot's dispatcher with re.match(trailing_part), so it 
will only match the start of the payload.

- **.rule = str()** : a string to be passed to re.compile(), used
  for matching against the payload of every event (ie. after the 
  second ':' mark).  If it matches, launch the function and pass the 
  MatchObject as cmd_in.match .  the string can have '$nick' in it 
  which will be converted to the bot's nickname at load time; 
  changing the bot's nick later will not update this rule.
- **.rule = (str(),str())** : identical to .rule = str()+str() but the
  '$nick' substitution only happens in the first string.
- **.rule = (list(),str())** : identical to 
  .rule = bot.config.prefix + r'(' + "|".join(list()) + r')\b(?: +(?:' + str() + r'))?'
  with no '$nick' substitution.
- **.rule = (str(),list(),str())** : identical to 
  .rule = (str()+"("+"|".join(list())+") +"+str()) with '$nick'
  substitution in the first str()
- **.commands = list()** : this is identical to
  .rule = (phenny.config.prefix+'('+"|".join(list())+')(?: +(.*))?')
- **.event** : which events to check .rule against. Defaults to 
  'PRIVMSG'.
- **.priority** : can be 'high', 'medium', or 'low'.  Defaults to 
  'medium'. Functions with 'high' priority are checked and launched
  first, then  'medium', then 'low'. Note well that a successful
  match and call of a phenny module will *not* stop phenny from 
  continuing to check all modules's rules and commands for matches
  and possibly launching more functions.
- **.thread** : whether to give this function to a thread of its own
  for processing.  Defaults to True.
- **.example** : short example of use.  Seems only to be used by
  the phenny module 'info', which is not loaded by default.
- **.name** : not sure. defaults to the function's .\_\_name\_\_
- **.example** : not sure. defaults to .\_\_doc\_\_

When making a module that uses both rules and commands, remember
that the command-word will put the command in cmd_in.group(1) and
anything following it into cmd_in.group(2), so put a superfluous
group in your rule before the bit you want.  
ie: `command = ['smooch']` and `rule = r'$nick[,:] (smooch|kiss) +(.+)'`

If you need to remember something between calls of the function (ie 
cooldowns, playing tag), it is a poor idea to use the `global` 
statement as that uses the topmost namespace, not the module's, so 
it could cause collisions.  Instead, add another attribute to the 
function alongsite the ones mentioned above, and get/set it via 
`phenny.bot.variables['*funcname*'].*attrib*` . 

## step 6 ##

Bonus!  If the module has a function called 'setup(phenny)', it will
be launched right after the module is imported.  Beware that sometimes
it will be passed the real Phenny instance, and sometimes, like if
it's being reloaded, a PhennyWrapper.  Use the following to make sure
you always have the real deal:

    if hasattr(phenny, 'bot') :
      phenny = phenny.bot

The setup(phenny) function is good for starting threads if you want
your bot to monitor something outside IRC, like a website-update
notifier bot, or maybe a twitter gateway.  See the 'threadtest.py'
module that you should be able to find with this document.

Example module
--------------

    """ docstring that announces this is a phenny module
        and quickly defines the module's purpose.  Maybe some
        author information and a licence statement.
    """
    import random, time

    COOLDOWN = 60 * 5 # five-minute cooldown period
    NAMES = ['John', 'Rose', 'Dave', 'Jade', 'Aradia', 'Tavros', 
    'Sollux', 'Nepeta', 'Karkat', 'Kanaya', 'Terezi', 'Vriska', 
    'Equius', 'Gamzee', 'Eridan', 'Feferi']

    def crackship(phenny, cmd_in):
      " utters a nonsense romance pairing of two characters "
      now = time.time()
      self = phenny.bot.variables['crackship'] 
      if self.atime + COOLDOWN < now :
        random.shuffle(NAMES)
        name_l = cmd_in.group(2)
        if name_l and not name_l in NAMES:
          name_l = name_l.title()
        if not name_l in NAMES:
          name_l = NAMES[0]
          name_r = NAMES[1]
        elif name_l == NAMES[0]:
          name_r = NAMES[1]
        else:
          name_r = NAMES[0]
        phenny.say("I ship %s with %s" % (name_l, name_r))
        self.atime = now
      else:
        delay = self.atime + COOLDOWN - now
        phenny.bot.msg(cmd_in.nick,"%d second cooldown" % (delay))

    crackship.priority = 'medium'
    crackship.event = 'PRIVMSG'
    crackship.thread = False # no need, doesn't block on i/o
    crackship.rule = r'.*(ship|ships|shipped) (\S+) (?:and|with) \S+'
    crackship.commands = ['ship','crackship']
    crackship.atime = 0  # better to use func attribs than 'global'
