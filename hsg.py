"""
Phenny module to find the most likely thread asked for in 4chan
subforums. First version was written by Tatpurusha for !!c1Qf, depended
on neet.tv This version written by Mozai for !!c1Qf, uses 4chan API

This is free and unencumbered software released into the public domain.
"""
from __future__ import division, print_function
import httplib, json, re, time
from urlparse import urlparse
__version__ = '20130727'
# I'd like to import Mozai's fourchan.py, but I phenny is a bit weird about
# importing local modules, so I'll copy-paste instead.
# 2013-07-27: Cloudflare is blocking python urllib requests
#             need to cosplay as a human's browser

# -- config
# how many seconds between people asking?
# (0 means ignore, <0 means refuse. defaults to 60 seconds)
COOLDOWNS = {
  '#test2':15,
  '#farts':200,
  'lmotep':-1,
}

# how many catalog pages to fetch. smaller -> faster,
# but risk missing threads that are sinking.
PAGELIMIT = 9

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
    'regexp':'(hom[eo]st?uck|hamsteak)',
  },
  'cgl': {
    'board':'cgl',
    'regexp':'homestuck|vriska|nepeta|troll horns',
  },
  'draw': {
    'board':'co',
    'regexp':'drawthread',
  },
#  'foo': {
#    'board':'co',
#    'regexp':'the',
#  },
}

# When Cloudflare asks if we're a bot, this is what we answer
USER_AGENT = ' '.join(('Mozilla/5.0 (Macintosh; U; Intel Mac OS X; en-ca)',
                      'AppleWebKit/537+ (KHTML, like Gecko) Version/5.0',
                      'Safari/537.6+',
                      'Midori/0.4',
                     ))

# -- init
API_CATALOG = 'http://api.4chan.org/%s/%d.json' # (board, range(PAGELIMIT))
API_THREAD = 'http://api.4chan.org/%s/res/%d.json' # (board, thread_no)
HTML_CATALOG = 'http://boards.4chan.org/%s/catalog' # (board)
HTML_CATALOG_RE = r'<script[^>]*?type=.?text/javascript.?>\s*var\s+catalog\s*=\s*(.+?)</script>'
CATALOG_ORDER_TYPES = [ 'absdate', 'date', 'alt', 'r' ]
THREADURL = 'https://boards.4chan.org/%s/res/%d' # (board, thread_no)
BOARDCACHE = dict()
THREADCACHE = dict()
HTTP_HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Cache-Control': 'max-age=0',
    'Accept-Language': 'en-us;q=1.0',
    'Connection': 'Keep-Alive',
}

for S in SEARCHES:
    SEARCHES[S].setdefault('atime', 0)
for s in SEARCHES:
    if not (s.isalnum
            and SEARCHES[s].get('board', '').isalnum()
            and SEARCHES[s].get('regexp')
           ):
        raise ValueError('bad data in SEARCHES[%s]; refusing to start' % s)
    SEARCHES[s]['regexp'] = re.compile(SEARCHES[s]['regexp'], re.I)
HTML_CATALOG_REGEX = re.compile(HTML_CATALOG_RE, re.I)

def _timestamp_to_4chantime(thyme):
    " because sometimes 4chan api forgets to include its datestrings "
    return time.strftime('%m/%d/%y(%a)%H:%M', time.localtime(float(thyme)))

def _cleanse_posts_list(posts):
    """ Feb 2013: 4chan API now has inconsistent data types.
        Strings that match /^[0-9]$/ get turned into integers
        Some (not all) integers get turned into strings.
        Fuck, moot; get your shit together.
    """
    for i in posts:
        for j in ['no', 'time', 'resto']:
            if j in i:
                i[j] = int(i[j])
        for j in ['name', 'filename', 'sub', 'com']:
            if j in i:
                i[j] = unicode(i[j])
    return posts

def _cleanse_catalog_order(orderdict):
    """ sometimes the lists appear as dict instead of list
        and sometimes the thread ID
        it may never be fixed because PHP lists act exactly like dicts
        which makes you wonder how inefficient PHP lists are
    """
    for i in CATALOG_ORDER_TYPES:
        if i not in orderdict:
            orderdict[i] = orderdict['no']
        elif isinstance(orderdict[i], dict):
            newlist = [ orderdict[i][j] for j in sorted(orderdict[i].keys()) ]
            orderdict[i] = newlist
        elif isinstance(orderdict[i], list):
            continue
        else:
            raise ValueError("Bad data type for json_dict['order']['%s']: %s" % (i, type(orderdict[i])) )
    return orderdict

def _get_threads(board):
    """ given a 4chan subforum id, returns a list of thread-starting posts
        uses the 4chan Catalog webpages, faster than the JSON API
    """
    threads = []
    url = urlparse(HTML_CATALOG % board)
    conn = httplib.HTTPConnection(url.netloc, timeout=5)
    conn.request('GET', url.path, headers=HTTP_HEADERS)
    res = conn.getresponse()
    if res.status >= 200 and res.status < 300:
        page_content = res.read() # need it for diagnostics
        json_string = HTML_CATALOG_REGEX.search(page_content).group(1)
        json_string = json_string[:json_string.rindex('};')+1]
        json_dict = json.loads(json_string)
        json_dict['order']['no'] = sorted(json_dict['threads'].keys())
        json_dict['order'] = _cleanse_catalog_order(json_dict['order'])
        threadorder = json_dict['order']['no']
        if 'alt' in json_dict['order']:
            threadorder = json_dict['order']['alt']
        for i in threadorder:
            try:
                # Feb 2013: the 'order' lists are integers. but the 'threads'
                #   object is keyed on strings-of-integer
                #   LOL PHP DUNTCARE MAGIC TYPE CASTING HERF DERF
                this_thread = json_dict['threads'][i]
            except KeyError:
                if json_dict['threads'].has_key(str(i)):
                    this_thread = json_dict['threads'][str(i)]
                elif json_dict['threads'].has_key(unicode(i)):
                    this_thread = json_dict['threads'][unicode(i)]
                elif json_dict['threads'].has_key(int(i)):
                    this_thread = json_dict['threads'][int(i)]
                else:
                    raise ValueError("%s is not a valid thread ID" % i)
            this_thread['board'] = board
            # now some cooking because the catalog JSON doesn't match the API JSON
            this_thread['no'] = int(i)
            this_thread['replies'] = this_thread['r']
            this_thread['images'] = this_thread['i']
            this_thread['tim'] = this_thread.get('imgurl','deleted')
            this_thread['time'] = this_thread['date']
            this_thread['ctime'] = this_thread['date']
            this_thread['mtime'] = this_thread['date']
            this_thread['now'] = _timestamp_to_4chantime(this_thread['date'])
            this_thread['com'] = this_thread['teaser']
            this_thread['resto'] = 0
            threads.append(this_thread)
    else:
        print("*** http status %d when trying to fetch %s" % (res.status, url.geturl()))
    conn.close()
    if len(threads) == 0:
        # moot probably broke the catalog. Again.
        # fall back to fetching all the json for each forum page
        print("... did not find catalog json in %s ; trying API" % url.geturl())
        return _get_threads_api(board)
    _cleanse_posts_list(threads)
    return threads

def _get_threads_api(board):
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
        url = urlparse(API_CATALOG % (board, 0))
        conn = httplib.HTTPConnection(url.netloc, timeout=5)
        try:
            for i in range(PAGELIMIT):
                url = urlparse(API_CATALOG % (board, i))
                conn.request('GET', url.path, headers=HTTP_HEADERS)
                res = conn.getresponse()
                if res.status >= 200 and res.status < 300:
                    json_dict = json.loads(res.read())
                    for j in json_dict['threads'] :
                        # j is the thread, ['posts'][0] is the first post in thread
                        thread = j['posts'][0]
                        # ctime = thread creation time
                        thread['ctime'] = float(j['posts'][0]['time']) 
                        # mtime = thread last-modified time
                        thread['mtime'] = float(j['posts'][-1]['time'])
                        BOARDCACHE[board]['threads'].append(j['posts'][0])
                    res.close()
                else:
                    if (i > 0 and res.status == 404):
                        # we just went beyond the pages for that board, no biggie
                        pass
                    else:
                        print("*** bad http status %d for %s" % (res.status, url.geturl()))
                        res.close()
                    break
        except ValueError:
            # thrown by json.loads() for a HTTP-but-not-JSON response
            # usually safe to ignore; mostly don't want to scare the normals
            # with the shout-out from phenny.bot.error()
            print("*** did not find JSON in %s" % url.geturl())
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
        url = urlparse(API_THREAD % (board, thread_no))
        conn = httplib.HTTPConnection(url.netloc, timeout=5)
        conn.request('GET', url.path, headers=HTTP_HEADERS)
        res = conn.getresponse()
        try:
            if res.status >= 200 and res.status < 300 :
                json_dict = json.loads(res.read())
                posts = json_dict['posts']
            else:
                print("*** bad http status %d for url %s" % (res.status, url.geturl()))
                posts = []
        except ValueError:
            print("*** did not get JSON from %s" % url.geturl())
            # return empty list
        res.close()
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
        centage = ((now - int(ptimes[-cent])) // 60)
        if centage :
            posts[0]['ppm'] = (cent/centage)
        cent = int(len(itimes)*.1)
        centage = ((now - int(itimes[-cent])) // 60)
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
        return "not very long"

def tell_4chan_thread(phenny, cmd_in):
    " announces a thread from one of the pre-defined searches "
    now = time.time()
    cooldown = COOLDOWNS.get(cmd_in.sender, 60)
    searchconfig = SEARCHES.get(cmd_in.group(1))
    
    if cmd_in.admin :
        pass
    elif (cooldown == None) or (searchconfig == None):
        return
    elif cooldown < 0 :
        phenny.bot.msg(cmd_in.nick, REFUSETEXT)
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
        good_threads.sort(cmp=_cmp_thread_freshness, reverse=True)
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
        mesg += " (%s)" % (_secsToPretty(now - the_thread['ctime']))
        mesg += " %dp" % (the_thread.get('replies', 0) + 1)
        mesg += " %di" % (the_thread.get('images', 0) + 1)
        if the_thread.get('bans', 0) > 0 :
            # \x0305: mIRC colour code for red foreground
            mesg += " \x0305 %d bans\x03" % (the_thread['bans'])
        if the_thread.get('ppm') and the_thread['ppm'] > 0.1 :
            mesg += "; %.1f ppm" % the_thread['ppm']
        else :
            mesg += "; last post %s ago" % (_secsToPretty(now - the_thread['mtime']))
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
        good_threads.sort(cmp=_cmp_thread_freshness, reverse=True)
        for the_thread in good_threads :
            threadurl = THREADURL % (board, the_thread['no'])
            mesg = threadurl
            mesg += " \"%s\"" % the_thread.get('sub',"")
            mesg += " (c:%s)" % (_secsToPretty(now - the_thread['ctime']))
            mesg += " (m:%s)" % (_secsToPretty(now - the_thread['mtime']))
            mesg += " %dp" % (the_thread.get('replies', 0) + 1)
            mesg += " %di" % (the_thread.get('images', 0) + 1)
            phenny.msg(cmd_in.nick, mesg)
        phenny.msg(cmd_in.nick, "search complete")
    else :
        phenny.msg(cmd_in.nick, 'nothing found.')

tell_4chan_allthreads.priority = 'low'
tell_4chan_allthreads.thread = True
tell_4chan_allthreads.commands = [ c+".all" for c in SEARCHES.keys() ]

if __name__ == '__main__':
    print("--- Testing phenny module")
    from phennytest import PhennyFake, CommandInputFake
    COOLDOWNS['#test'] = 0
    FAKEPHENNY = PhennyFake()
    for SRCH in SEARCHES:
        print("** %s **" % SRCH)
        FAKECMD = CommandInputFake('.'+SRCH)
        tell_4chan_thread(FAKEPHENNY, FAKECMD)
