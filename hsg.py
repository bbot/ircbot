"""
Phenny module to find the most likely thread asked for in 4chan
subforums. First version was written by Tatpurusha for !!c1Qf, depended
on neet.tv This version written by Mozai for !!c1Qf, uses 4chan API

This is free and unencumbered software released into the public domain.
"""
from __future__ import division
import time, re, json, urllib
__version__ = '20121128'
# I'd like to import Mozai's fourchan.py, but I phenny is a bit weird about
# importing local modules, so I'll copy-paste instead.

# -- config
# how long between people asking? (0 means ignore, <0 means refuse)
COOLDOWNS = {
  '#test':15,
  '#farts':200,
  'lmotep':-1,
}

# how many catalog pages to fetch. smaller -> faster,
# but risk missing threads that are sinking.
PAGELIMIT = 10

# what to say when refusing
REFUSETEXT = 'No.'

# how many seconds to cache 4chan data; moot said 10 seconds at least.
CACHE_AGELIMIT = 60

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
API_CATALOG = 'http://api.4chan.org/%s/%d.json' # (board, range(PAGELIMIT))
API_THREAD = 'http://api.4chan.org/%s/res/%d.json' # (board, thread_no)
THREADURL = 'https://boards.4chan.org/%s/res/%d' # (board, thread_no)
BOARDCACHE = dict()
THREADCACHE = dict()

for S in SEARCHES:
    SEARCHES[S].setdefault('atime', 0)
for s in SEARCHES:
    if not (s.isalnum
            and SEARCHES[s].get('board', '').isalnum()
            and SEARCHES[s].get('regexp')
           ):
        raise ValueError('bad data in SEARCHES[%s]; refusing to start' % s)
    SEARCHES[s]['regexp'] = re.compile(SEARCHES[s]['regexp'], re.I)


def _get_threads(board):
    " returns a list() of posts that start each thread on a 4chan board "
    if ((not board.isalnum()) or (len(board) > 3)) :
        raise ValueError("%s doesn't look like a valid 4chan board id" % board)
    if not BOARDCACHE.get(board):
        BOARDCACHE[board] = { 'mtime':0, 'threads':list() }
    now = time.time()
    for i in BOARDCACHE.keys():
        # garbage collection
        if ((BOARDCACHE[i]['mtime'] + CACHE_AGELIMIT) <= now ):
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
                        thread = j['posts'][0]
                        # ctime = thread creation time
                        thread['ctime'] = j['posts'][0]['time'] 
                        # mtime = thread last-modified time
                        thread['mtime'] = j['posts'][-1]['time']
                        BOARDCACHE[board]['threads'].append(j['posts'][0])
                    resp.close()
                elif resp.code >= 400:
                    # 403 denied, 404 we went beyond the catalog, or 500 server puked.
                    resp.close()
                    break
        except ValueError:
            # thrown by json.loads() for a HTTP-but-not-JSON response
            # usually safe to ignore; mostly don't want to scare the normals
            # with the shout-out from phenny.bot.error()
            pass
    return BOARDCACHE[board]['threads']

def _cmp_thread_freshness(i, j):
    " for use in list().sort() to order threads fresh to stale "
    # a heuristic that DOES NOT download every post of every thread
    if i.get('imagelimit') or i.get('images', 0) < 8:
        return -1  # i must be less fresh, or too fresh
    elif j.get('imagelimit') or j.get('images', 0) < 8:
        return 1   # j must be less fresh, or too fresh
    left = i['mtime']
    right = j['mtime']
    return cmp(left, right)

def _get_posts(board, thread_no):
    "given a 4chan subforum id & thread #, fetches list of post dict()"
    if not board.isalnum():
        raise ValueError("'%s' is not a valid 4chan subforum" % board)
    try:
        thread_no = int(thread_no)
    except ValueError:
        raise ValueError("'%s' is not a valid thread id number" % thread_no)
    now = time.time()
    thread_id = "%s/%s" % (board, thread_no)
    for i in THREADCACHE.keys():
        # garbage collection
        if ((THREADCACHE[i]['mtime'] + CACHE_AGELIMIT) <= now ):
            del(THREADCACHE[i])
    if thread_id not in THREADCACHE :
        THREADCACHE[thread_id] = { 'posts': None, 'mtime': 0 }
        posts = list()
        sock = urllib.urlopen(API_THREAD % (board, thread_no))
        try:
            if sock.code >= 200 and sock.code < 300 :
                json_dict = json.loads(sock.read())
                posts = json_dict['posts']
        except ValueError:
            pass # return empty list if we got a non-JSON response
        sock.close()
        # start posts-per-minute and images-per-minute
        ptimes = list()
        itimes = list()
        for post in posts:
            post.setdefault('board', board)
            if post.get('time'):
                ptimes.append(post['time'])
                if post.get('filename'):
                    itimes.append(post['time'])
        cent = int(len(ptimes)*.1)
        centage = ((now - ptimes[-cent]) // 60)
        if centage :
            posts[0]['ppm'] = (cent/centage)
        cent = int(len(itimes)*.1)
        centage = ((now - itimes[-cent]) // 60)
        if centage :
            posts[0]['ipm'] = (cent/centage)
        THREADCACHE[thread_id] = { 'posts':posts, 'mtime': now }

    return THREADCACHE[thread_id]['posts']


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
    " announces a thread from one of the pre-defined searches "
    now = time.time()
    cooldown = COOLDOWNS.get(cmd_in.sender)
    searchconfig = SEARCHES.get(cmd_in.group(1))

    if (cooldown == None) or (searchconfig == None):
        return
    if cooldown < 0 :
        phenny.bot.msg(cmd_in.nick, REFUSETEXT)
        return
    elif cooldown == 0:
        return
    elif (searchconfig['atime'] + cooldown) > now :
        # cooldown hasn't expired; do nothing
        return

    board = searchconfig['board']
    regexp = searchconfig['regexp']
    threads = _get_threads(board)
    good_threads = [ i for i in threads if regexp.search(i.get('sub','')) ]
    if not good_threads :
        good_threads = [ i for i in threads if regexp.search(i.get('com','')) ]

    if good_threads :
        good_threads.sort(cmp=_cmp_thread_freshness)
        the_thread = good_threads[0]
        threadurl = THREADURL % (board, the_thread['no'])
        # -- start time-expensive bit
        # ceequof might wish to disable it
        the_posts = _get_posts(board, the_thread['no'])
        the_thread['ppm'] = the_posts[0].get('ppm')
        the_thread['ipm'] = the_posts[0].get('ipm')
        # -- end time-expensive bit
        mesg = threadurl
        mesg += " \"%s\"" % the_thread.get('sub',"")
        mesg += " (%s)" % (_secsToPretty(now - the_thread['time']))
        mesg += " %dp" % (the_thread.get('replies', 0) + 1)
        mesg += " %di" % (the_thread.get('images', 0) + 1)
        if the_thread.get('bans', 0) > 0 :
            # \x0305: mIRC colour code for red foreground
            mesg += " \x0305 %d bans\x03" % (the_thread['bans'])
        if the_thread.get('ppm') and the_thread['ppm'] > 0.1 :
            mesg += "; %.1f ppm" % the_thread['ppm']
        searchconfig['atime'] = now
    else:
        mesg = '...'
        # force ignoring for a while; 10 seconds is m00t's idea from the API
        searchconfig['atime'] = now - cooldown + 10
    phenny.say(mesg)

tell_4chan_thread.priority = 'medium'
tell_4chan_thread.thread = True  # I might block on net i/o
tell_4chan_thread.commands = SEARCHES.keys()

def tell_4chan_allthreads(phenny, cmd_in):
    """ used by admins for diagnosing problems 
    with _get_threads and _cmp_thread_freshness
    """
    if not cmd_in.admin:
        return
    now = time.time()
    searchconfig = SEARCHES.get(cmd_in.group(1).replace('.all',''))
    board = searchconfig['board']
    regexp = searchconfig['regexp']

    phenny.msg(cmd_in.nick, 'searching; board: "%s", regexp: "%s"' % (board, regexp.pattern))
    threads = _get_threads(board)
    good_threads = [ i for i in threads if regexp.search(i.get('sub','')) ]
    if not good_threads :
        good_threads = [ i for i in threads if regexp.search(i.get('com','')) ]

    if good_threads :
        good_threads.sort(cmp=_cmp_thread_freshness)
        for the_thread in good_threads :
            threadurl = THREADURL % (board, the_thread['no'])
            mesg = threadurl
            mesg += " \"%s\"" % the_thread.get('sub',"")
            mesg += " (%s)" % (_secsToPretty(now - the_thread['time']))
            mesg += " %dp" % (the_thread.get('replies', 0) + 1)
            mesg += " %di" % (the_thread.get('images', 0) + 1)
            phenny.msg(cmd_in.nick, mesg)
        phenny.msg(cmd_in.nick, "search complete")
    else :
        phenny.msg(cmd_in.nick, 'nothing found.')

tell_4chan_allthreads.priority = 'low'
tell_4chan_allthreads.thread = True
tell_4chan_allthreads.commands = [ c+".all" for c in SEARCHES.keys() ]

# if __name__ == '__main__':
#  print "--- Testing phenny module"
#  from phennytest import PhennyFake, CommandInputFake
#  COOLDOWNS['#test'] = 0
#  FAKEPHENNY = PhennyFake()
#  for SRCH in SEARCHES:
#    print "** %s **" % SRCH
#    FAKECMD = CommandInputFake('.'+SRCH)
#    tell_4chan_thread(FAKEPHENNY, FAKECMD)
