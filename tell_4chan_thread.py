"""
Phenny module to find the most likely thread asked for in 4chan
subforums. First version was written by Tatpurusha for !!c1Qf, depended
on neet.tv This version written by Mozai for !!c1Qf, uses 4chan API

This is free and unencumbered software released into the public domain.
"""
__version__ = '20121110'
import time, re, json, urllib
# I'd like to import Mozai's fourchan.py, but I have no goddamn clue
# how phenny handles importing of local modules, so I'll copy-paste instead.

# -- config
# how long between people asking? (-1 means to refuse when asked.)
COOLDOWNS = { '#farts':300, 'lmotep':-1 }

# what to say when refusing, and how often
REFUSETEXT = 'No.'
REFUSECOOLDOWN = 60

# how many seconds to cache a 4chan board's catalog
BOARDCACHE_AGELIMIT = 60

# what we can ask to look for
#   SEARCHES = { 'bat': { board: 'co', regexp:'batman' } }
# creates command
#   !bat
# which will reply with
#   "http://4chan.org/co/res/14355 'Batman sucks' (2h 3m old) "

SEARCHES = { 'hsg': { 'board':'co',  # where do I search
                      'regexp':'hom[eo]st?uck|hamsteak', # what to look for
                    },
            'cgl': { 'board':'cgl',
                     'regexp':'homestuck|vriska|nepeta',
                   },
           }


# -- init
API_CATALOG = 'http://api.4chan.org/%s/%d.json' # (board, range(15))
PAGELIMIT = 15  # catalog pages 0 to PAGELIMIT-1; smaller -> faster
THREADURL = 'https://boards.4chan.org/%s/res/%d' # (board, thread_no)
BOARDCACHE = dict()

for s in SEARCHES:
  if not (s.isalnum and s.get('board', '').isalnum() and s.get('regexp')):
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
        sock = urllib.urlopen(API_CATALOG % (board, i))
        if sock.code >= 200 and sock.code < 300:
          json_dict = json.loads(sock.read())
          for j in json_dict['threads'] :
            # j is the thread, ['posts'][0] is the first post in thread
            BOARDCACHE[board]['threads'].extend(j['posts'][0])
          sock.close()
        elif sock.code >= 400:
          # 403 denied, 404 we went beyond the catalog, or 500 server puked.
          sock.close()
          break
    except ValueError:
      # thrown by json.loads() for a HTTP-but-not-JSON response
      # TODO: raise an error to get a human's attention for this
      pass
    # inserting a sleep here so I don't shoot myself in the foot later
    time.sleep(1)
  return len(BOARDCACHE[board]['threads'])

def _cmp_thread_freshness(i, j):
  """ for use in list().sort() to order threads fresh to stale
  """
  # TODO: better heuristic.  I used to use ctime + 60 * posts + 60 * images,
  #       but gives too much weight for threads that hit img-limit.
  left = i['time']
  right = j['time']
  return cmp(left, right)

def _get_recent_thread(board, regexp):
  # outside hsg() so we can test it by running this on its own
  _update_boardcache(board)  # using side effects! hiss!!!
  threads = list()
  for i in BOARDCACHE[board]['threads']:
    thread = BOARDCACHE[board]['threads'][i]
    if regexp.search(thread.get('sub','')) :
      threads.append(thread)
    elif regexp.search(thread.get('com','')) :
      threads.append(thread)
  if threads :
    threads.sort(cmp=_cmp_thread_freshness, reverse=True)
    return threads[0]
  else :
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

def tell_4chan_thread(phenny, data):
  " announces what is most likely the Homestuck thread "
  now = time.time()
  cooldown = COOLDOWNS.get(data.sender)
  # data.sender could be the message src or the destination. derp.
  # as a command, data.group(1) is the command sans prefix
  # as a command, data.group(2) is None or everything after command + space
  searchconfig = SEARCHES.get(data.group(1))

  if (not cooldown) or (not searchconfig):
    return
  if cooldown < 0 :
    # negative cooldown means refuse...
    if -(cooldown) <= now :
      phenny.msg(data.nick, REFUSETEXT)
      # ... and tells us when we explicitly refuse again.
      COOLDOWNS[data.nick] = -(now + REFUSECOOLDOWN)
    return
  if (searchconfig.get('atime', 0) + cooldown) <= now :
    return

  the_thread = _get_recent_thread(searchconfig['board'], searchconfig['regexp'])

  if the_thread :
    # make URL, analyze for age & post counts
    mesg = THREADURL % (searchconfig['board'], the_thread['no'])
    # if the_thread['sub']:
    #  mesg += " \"%s\"" % the_thread['sub']
    mesg += " ("
    mesg += " %s old" % _secsToPretty(now - the_thread['time'])
    mesg += " %dp" % the_thread['omitted_posts']
    mesg += " %di" % the_thread['omitted_images']
    mesg += ")"
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
  for SRCH in SEARCHES:
    print "** %s **" & SRCH
    print _get_recent_thread(SEARCHES[SRCH]['board'], SEARCHES[SRCH]['regexp'])

# TODO: better heuristic to avoid fetching ALL pages for a subforum
#       without missing out if there's a shitty positive result on page 1
#       but the good positive result is on page 15.
# TODO: improve _cmp_thread_freshness()

# phenny loads a module, walks module.iteritems() and if it has an
#   attribute 'commands' or 'rule', then it adds it as a hook. I can't
#   explicitly hook nor unhook stuff.  derp?
# also: example code uses 'input' as a function paramter, when
#   that is already __builtin__.input() .  Derpity derp.
# see also how phenny uses 'data.sender' two hold one of two distinct
#   pieces of data, and you have to figure out which at runtime.
#   hurp de-derp.

