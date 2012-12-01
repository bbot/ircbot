" a demonstration of doing threading in a phenny module "
import time, threading

# the pause between emissions from the loop
DELAY = 5

def threadtest_loop(phenny):
  " a loop that sits and spins "
  my_thread_name = threading.current_thread().name
  while phenny.threadtest_name == my_thread_name :
    time.sleep(DELAY)
    if not phenny.threadtest_name == my_thread_name :
      break
    now = time.asctime(time.localtime())
    for target in phenny.channels :
      phenny.msg(target, "%s %s" % (my_thread_name, now))
  for target in phenny.channels :
    phenny.msg(target,'%s stopped' % my_thread_name)

def threadtest_stop(phenny, cmd_in):
  " munges a semaphore, threadtest_loop will commit sudoku "
  del(cmd_in) # shut up pylint
  phenny.say('stopping %s' % (phenny.bot.threadtest_name))
  phenny.bot.threadtest_name = None

threadtest_stop.commands = ['threadteststop','ttstop']

def setup(phenny):
  " starts loopy() "
  # Sometimes I get the realy Phenny instance,
  # but sometimes I get PhennyWrapper.
  # PhennyWrapper was such a bad idea; never saw the point.
  if hasattr(phenny, 'bot') :
    phenny = phenny.bot
  thr_args = (phenny,)
  thr = threading.Thread(target=threadtest_loop, args=thr_args)
  # Adding arbitrary attributes to the bot instance is ugly, 
  # but it seems phenny doesn't have another way
  phenny.threadtest_name = thr.name
  thr.start()

