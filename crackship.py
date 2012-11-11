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
COOLDOWN = 300

# collection of names
NAMES = """Aradia Tavros Sollux Nepeta Karkat Kanaya
           Terezi Vriska Equius Gamzee Eridan Feferi
           John Rose Dave Jade Jane Roxy Dirk Jake
        """

if isinstance(NAMES, basestring):
  NAMES = NAMES.split()

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

