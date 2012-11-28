"""
Phenny module to find the most likely thread asked for in 4chan
subforums. First version was written by Tatpurusha for !!c1Qf, depended
on neet.tv This version written by Mozai for !!c1Qf, uses 4chan API

This is free and unencumbered software released into the public domain.
"""
from __future__ import division
import time, re, json, urllib
__version__ = '20121110'
# I'd like to import Mozai's fourchan.py, but I phenny is a bit weird about
# importing local modules, so I'll copy-paste instead.

# -- config
# how long between people asking? (-1 means to refuse when asked.)
COOLDOWNS = { 
  '#test':2, 
  '#farts':300, 
  'lmotep':-1, 
  'torridGristle':-1,
}

# what to say when refusing, and how often
REFUSETEXT = 'No.'
REFUSECOOLDOWN = 60

# how many seconds to cache a 4chan board's catalog
BOARDCACHE_AGELIMIT = 60

# what we can ask to look for
#   SEARCHES = { 'bat': { board: 'co', regexp:'batman' } }
# creates command
#   .bat
# which will reply with
#   "http://4chan.org/co/res/14355 'Batman sucks' (2h 3m old) "

SEARCHES = { 
  'hsg': { 
    'board':'co',
    'regexp':'(hom[eo]st?uck|hamsteak) general',
  },
  'cgl': { 
    'board':'cgl',
    'regexp':'homestuck|vriska|nepeta|troll horns',
  },
}


# -- init
PAGELIMIT = 15  # catalog pages 0 to PAGELIMIT-1; smaller -> faster
API_CATALOG = 'http://api.4chan.org/%s/%d.json' # (board, range(PAGELIMIT))
THREADURL = 'https://boards.4chan.org/%s/res/%d' # (board, thread_no)
BOARDCACHE = dict()
for S in SEARCHES:
  SEARCHES[S].setdefault('atime', 0)

for s in SEARCHES:
  if not (s.isalnum 
          and SEARCHES[s].get('board', '').isalnum() 
          and SEARCHES[s].get('regexp')
         ):
    raise ValueError('bad data in SEARCHES[%s]; refusing to start' % s)
  SEARCHES[s]['regexp'] = re.compile(SEARCHES[s]['regexp'], re.I)


def _update_boardcache(board):
  " refresh the data in BOARDCACHE if necessary "
  if ((not board.isalnum()) or (len(board) > 3)) :
    raise ValueError("%s doesn't look like a valid 4chan board id" % board)
  if not BOARDCACHE.get(board):
    BOARDCACHE[board] = { 'mtime':0 }
  now = time.time()
  for i in BOARDCACHE:
    # garbage collection
    if ((BOARDCACHE[i]['mtime'] + BOARDCACHE_AGELIMIT) <= now ):
      BOARDCACHE[i]['threads'] = list()
  if len(BOARDCACHE[board]['threads']) == 0 :
    # cache for this board was stale, unused, or useless
    try:
      for i in range(PAGELIMIT):
        resp = urllib.urlopen(API_CATALOG % (board, i))
        if resp.code >= 200 and resp.code < 300:
          json_dict = json.loads(resp.read())
          for j in json_dict['threads'] :
            # j is the thread, ['posts'][0] is the first post in thread
            BOARDCACHE[board]['threads'].append(j['posts'][0])
          resp.close()
        elif resp.code >= 400:
          # 403 denied, 404 we went beyond the catalog, or 500 server puked.
          resp.close()
          break
    except ValueError:
      # thrown by json.loads() for a HTTP-but-not-JSON response
      # use phenny.error() ?  if they bothered documenting it, tabernaq
      pass
    # inserting a sleep here so I don't shoot myself in the foot later
    time.sleep(1)
  return len(BOARDCACHE[board]['threads'])

def _cmp_thread_freshness(i, j):
  """ for use in list().sort() to order threads fresh to stale
  """
  # needs a better heuristic.  I used to use
  # ctime + 60 * posts + 60 * images
  # but gives too much weight to threads that hit 250 img limit, 
  # which happens every 2.3 hours for homestuck threads on /co/
  left = i['time']
  right = j['time']
  return cmp(left, right)

def _get_matching_threads(board, regexp):
  # outside hsg() so we can test it by running this on its own
  _update_boardcache(board)  # using side effects! hiss!!!
  threads = list()
  # return a list of threads with matching subjects
  for thread in BOARDCACHE[board]['threads']:
    if regexp.search(thread.get('sub','')):
      threads.append(thread)
  # if no matching subjects, *then* check first post text
  if not threads:
    for thread in BOARDCACHE[board]['threads']:
      if regexp.search(thread.get('com','')) :
        threads.append(thread)
  if threads:
    threads.sort(cmp=_cmp_thread_freshness, reverse=True)
    return threads
  else:
    return None

def _secsToPretty(ticks=0):
  " given ticks as a duration in seconds, convert it to human-friendly units "
  day, remain    = divmod(ticks, (24*60*60))
  hour, remain   = divmod(remain, (60*60))
  minute, second = divmod(remain, 60)
  if (day > 0):
    return "%dd %dh" % (day, hour)
  elif (hour > 0):
    return "%dh %dm" % (hour, minute)
  elif (minute > 0):
    return "%dm %ds" % (minute, second)
  else:
    return "not very"

def tell_4chan_thread(phenny, cmd_in):
  " announces what is most likely the Homestuck thread "
  now = time.time()
  cooldown = COOLDOWNS.get(cmd_in.sender)
  searchconfig = SEARCHES.get(cmd_in.groups(0))
  if (cooldown == None) or (searchconfig == None):
    return

  if cooldown < 0 :
    # negative cooldown means refuse...
    if -(cooldown) <= now :
      # ... and refuse explictly if it's been long enough
      phenny.reply(REFUSETEXT)
      COOLDOWNS[cmd_in.sender] = -(now + REFUSECOOLDOWN)
    return
  if (searchconfig['atime'] + cooldown) > now :
    # cooldown hasn't expired; do nothing
    return

  the_threads = _get_matching_threads(searchconfig['board'], searchconfig['regexp'])
  if the_threads :
    the_thread = the_threads[0]
    # make URL, analyze for age & post counts
    mesg = THREADURL % (searchconfig['board'], the_thread['no'])
    # if the_thread['sub']:
    #  mesg += " \"%s\"" % the_thread['sub']
    mesg += " (%s)" % _secsToPretty(now - the_thread['time'])
    mesg += " %dp" % the_thread['replies']
    mesg += " %di" % the_thread['images']
    searchconfig['atime'] = now
  else:
    mesg = '...'
    # force ignoring for a while; 10 seconds is m00t's idea from the API
    searchconfig['atime'] = now - cooldown + 10
  phenny.say(mesg)

tell_4chan_thread.priority = 'medium'
tell_4chan_thread.commands = SEARCHES.keys()


if __name__ == '__main__':
  print "--- Testing phenny module"
  from phennytest import PhennyFake, CommandInputFake
  COOLDOWNS['#test'] = 0
  FAKEPHENNY = PhennyFake()
  for SRCH in SEARCHES:
    print "** %s **" % SRCH
    FAKECMD = CommandInputFake('.'+SRCH)
    tell_4chan_thread(FAKEPHENNY, FAKECMD)
