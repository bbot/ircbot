"""
Says 'no problem' when you say .thanks.

Useful for sticking print() statements into it and reloading
so you can do diagnostic or code introspection in a live bot.

This is free and unencumbered software  released into the public domain.
I wish our society wasn't so litigatious that I needed to say that.
"""

def thanks(phenny, cmd_in):
  " Responds in the same context with 'No problem.' "
  phenny.say("No problem.")
  del(cmd_in) # unused

thanks.commands = ['thanks']
# turns into r'.(thanks)(?: +(.*))'
thanks.rule = ('$nick','(thanks|thank you)')
# turns into r'aradiabot[,:] +(thanks|thank you)'
thanks.priority = 'low'

if __name__ == '__main__':
  # run 'python thanks.py' to test it
  from phennytest import PhennyFake, CommandInputFake
  print "--- Testing phenny module"
  FAKEPHENNY = PhennyFake()
  FAKECMD = CommandInputFake('.thanks')
  thanks(FAKEPHENNY, FAKECMD)

