"""
stuff for testing Phenny modules

example:

if __name__ == '__main__':
  import sys
  sys.path.append('.')  # why is this not default?
  sys.path.append('..') # in case phenny/modules/ is pwd
  from phennytest import PhennyFake, CommandInputFake
  PHENNYFAKE = PhennyFake()
  CMDFAKE = CommandInputFake('.wub a dub dub')
  wub(PHENNYFAKE, CMDFAKE)

"""
import re

class PhennyFake(object):
  " use in place of PhennyWrapped "
  @staticmethod
  def say(mmm): 
    "send message back to where command came from"
    print mmm
    return
  @staticmethod
  def reply(mmm):
    "send message back to who issued the command"
    print mmm
    return

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

