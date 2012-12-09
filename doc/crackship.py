""" phenny module written as an example of how to write
    phenny modules; supposed to accompany phenny_module_howto.md
    written by Mozai <moc.iazom@sesom> one Saturday afternoon
    Do I even need to put a license statement here?  I do?  Jeez.

    "This work is licensed under the Creative Commons
    Attribution-ShareAlike 3.0 Unported License. To view a copy of this
    license, visit http://creativecommons.org/licenses/by-sa/3.0/."
    No assurances of performance nor of safety are expressed or implied.
"""
import random, time

# delay between utterances; always a good idea with IRC bots.
COOLDOWN = 60 * 15 # 1: testing, 60 * 15 : normal 15 minute cooldown

# list() of names
NAMES = """
  John Rose Dave Jade
  WV PM AR WQ
  Aradia Tavros Sollux Nepeta Karkat Kanaya
  Terezi Vriska Equius Gamzee Eridan Feferi
  Slick Droog Deuce Boxcars
  Jane Roxy Dirk Jake
  Damara Rufioh Mituna Meulin Kankri Porrim
  Latula Aranea Horuss Kurloz Cronus Meenah
""".split()

# "Cronus": Hussie wrote in his will, just in case he died before
#   he could finish Homestuck, that "dualscar would never get
#   together with someone." Even a Leijon would not dare meddle.

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
    if name_l == 'Cronus':
      name_r = 'nobody'
    elif name_r == 'Cronus':
      name_r = NAMES[2]
    phenny.say("I ship %s with %s" % (name_l, name_r))
    self.atime = now
  # else:
    # delay = self.atime + COOLDOWN - now
    # phenny.bot.msg(cmd_in.nick,"%d second cooldown" % (delay))

crackship.priority = 'medium'
crackship.event = 'PRIVMSG'
crackship.thread = False  # don't bother, non-blocking func call
crackship.rule = r'.*(ship|ships|shipped) (\S+) (?:and|with) \S+'
crackship.commands = ['ship','crackship']
crackship.atime = 0  # better to write to func attributes than 'global'

if __name__ == '__main__':
  # run 'python crackship.py' to test it
  import sys
  sys.path.extend(('.','..')) # why is this necessary?
  from phennytest import PhennyFake, CommandInputFake
  print "--- Testing phenny module"
  COOLDOWN = -1
  FAKEPHENNY = PhennyFake()
  for i in range(6):
    FAKECMD = CommandInputFake('.ship')
    crackship(FAKEPHENNY, FAKECMD)
  print "(shipping John)   - ",
  FAKECMD = CommandInputFake('.ship John')
  crackship(FAKEPHENNY, FAKECMD)
  print "(shipping Karkat) - ",
  FAKECMD = CommandInputFake('.ship Karkat')
  crackship(FAKEPHENNY, FAKECMD)
