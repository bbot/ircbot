"""
stuff for testing Phenny modules

example:

if __name__ == '__main__':
  import sys
  sys.path.extend(('.','..')) # so we can find phennytest
  from phennytest import PhennyFake, CommandInputFake
  PHENNYFAKE = PhennyFake()
  CMDFAKE = CommandInputFake('.wub a dub dub')
  wub(PHENNYFAKE, CMDFAKE)

"""
import sys, re

class ConfigFake():
  " fakes the module created by importing ~/.phenny/phenny.conf "
  def __init__(self):
    self.nick = 'botnick'
    self.name = 'Phenny Palmersbot,'
    self.channels = ['#test']
    self.password = None
    self.owner = 'botowner'
    self.admins = [self.owner, 'botadmin']
    self.prefix = r'\.'
    
class PhennyFake(object):
  " use in place of PhennyWrapped "
  @staticmethod
  def say(mmm): 
    print mmm
  @staticmethod
  def reply(mmm):
    PhennyFake.say("nick: "+mmm)
  @staticmethod
  def write(args, trailing=None):
    mesg = ': '+' '.join(args)
    if trailing:
      mesg += ' :'+trailing
    print mesg
  @staticmethod
  def msg(destination, text):
    PhennyFake.write(('PRIVMSG', destination), text)
  @staticmethod
  def log(mesg):
    sys.stderr.write(mesg)
  def __init__(self, config=None):
    if not config:
      config = ConfigFake()
    if not hasattr(config,'prefix') or not config.prefix :
      config.prefix = r'\.'
    self.config = config
    self.doc = {}
    self.stats = {}
    self.variables = {}
    self.stack = list()

class CommandInputFake(unicode):
  " use in place of CommandInput "
  def __new__(cls, text):
    cmd_re = r'^[\.\!](\S+)(?: +(.*))?$'
    cif = unicode.__new__(cls, text)
    cif.sender = '#test'
    cif.nick = 'self'
    cif.event = 'PRIVMSG'
    cif.bytes = ':'+text
    cif.match = re.match(cmd_re, text)
    cif.groups = cif.match.groups
    cif.group = cif.match.group
    cif.args = ()
    return cif

