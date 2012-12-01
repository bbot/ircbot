"""
url_notify.py - Phenny module to check websites for updates
Rewritten again by Mozai
This is free and unencumbered software released into the public domain.
"""
import httplib, time, re, rfc822, socket, threading, urllib

# -- config
# global delay between checks
# any 'delay' setting in SITES less than this will act as 
# this number anyways.
LOOPDELAY = 30

# sites to check.
# 'cmd' : {   used for '.cmd' to report last mtime
#  'name': used when reporting last mtime and in default mesg
#  'url': 'http://host/path/blah',
#  'url': ('starting url', regexp to next url, regexpt to next url, ...)
#  'delay': minimum seconds between checks,
#  'dest': (channel to announce, nick to notify) , 
#          defaults to all channels bot was configured to join
#  'mesg': what do say. defaults to "${name} updated Xm Ys ago"
#  }

SITES = {
  'update' : {
    'name': 'MSPA',
    'url' : 'http://mspaintadventures.com/rss/rss.xml',
    'mesg': '===== UPDATE UPDATE UPDATE UPDATE =====\n' +
            '==== http://mspaintadventures.com/ ====\n'
  },
  'sbahj' : {
    'name': 'SBaHJ',
    'url' : ('http://mspaintadventures.com/sweetbroandhellajeff', 
            r'="(.*?)"><img src="new.jpg"',
            ),
    'delay': 60,
    'dest': ('#farts','Mozai'),
    'mesg': '= JESUS DICK ==================hornse==\n' +
            '=== THERSE A SWEET HELLA UPDTE ======-=\n'
  },
}
# TODO: elegant way of getting the 'click here' link into mesg
# TODO: elegant way of getting '5m 7s ago' text into mesg

# --- end config

for SITE in SITES:
  SITES[SITE]['mtime'] = 0
  SITES[SITE]['atime'] = 0
  SITES[SITE].setdefault('delay', LOOPDELAY)
  SITES[SITE].setdefault('name', SITE)
  # no setdefault('mesg'), not until we include click-here and age

def _secsToPretty(ticks=0):
  " given ticks as a duration in seconds, in human-friendly units "
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
    return "less than a minute"

def notify_owner(phenny, mesg):
  " carp to bot's owner, not to the channel "
  if hasattr(phenny,'bot'):
    phenny = phenny.bot
  try:
    ownernick = phenny.config.owner
    phenny.msg(ownernick, mesg)
  except AttributeError:
    # no owner configured? we carp to console anyways
    pass
  phenny.log('*** '+mesg)

def _update_siterecord(site):
  " update the SITES dict() if desired. may throw socket.timeout "
  now = time.time()
  url = site['url']
  if isinstance(url, (list, tuple)):
    # it's a chain
    url = site['url'][0]
    for step in site['url'][1:]:
      regexp = re.compile(step)
      (host, path) = urllib.splithost(url)
      conn = httplib.HTTPConnection(host, timeout=3)
      conn.request("GET", path)
      match = regexp.search(regexp)
      if match:
        url = urllib.basejoin(url, match.group(1))
      else:
        url = None
        break
  if not url :
    raise Exception("could not find url for %s" % site['name'])
  if url :
    (host, path) = urllib.splithost(url)
    connect = httplib.HTTPConnection(host, timeout=2)
    connect.request("HEAD", path)
    mtime = connect.getresponse().getheader('Last-Modified')
    if mtime:
      mtime = time.mktime(rfc822.parsedate(mtime))
      site['mtime'] = mtime
  site['atime'] = now

def url_notify_loop(phenny):
  " update SITES cache; if they changed recently carp about it "
  my_thread_name = threading.current_thread().name
  while phenny.notify_threadname == my_thread_name :
    now = time.time()
    for sitekey in SITES:
      if not phenny.notify_threadname == my_thread_name :
        break
      try:
        site = SITES[sitekey]
        _update_siterecord(site)
        if (now - site['mtime']) <= site['delay'] :
          mesg = site['mesg']
        if not mesg:
          when_ago = _secsToPretty(site['mtime'])
          mesg = "%s updated %s" % (site['name'], when_ago)
        targets = list(site.get('dest'))
        if not targets:
          targets = phenny.channels
        for dest in targets:
          for line in site['mesg'].split("\n") :
            phenny.msg(dest, line)
      except socket.timeout :
        notify_owner(phenny, "socket timeout updating %s" % site['name'])  
    if not phenny.notify_threadname == my_thread_name :
      time.sleep(LOOPDELAY)

def url_notify_stop(phenny, cmd_in):
  " munges a semaphore, notify_loop will commit sudoku "
  who = cmd_in.nick
  phenny.msg(who,'stopping notify (%s)' % (phenny.bot.notify_threadname))
  phenny.bot.notify_threadname = None

url_notify_stop.commands = ['notifystop','stopnotify']


def setup(phenny):
  " starts notify_loop() "
  # PhennyWrapper was such a bad idea; never saw the point.
  if hasattr(phenny, 'bot') :
    phenny = phenny.bot
  thr_args = (phenny,)
  thr = threading.Thread(target=url_notify_loop, args=thr_args)
  # The next line is ugly, but no other choice it seems.
  phenny.notify_threadname = thr.name
  thr.start()

def tell_last_update(phenny, cmd_in):
  " utters the last mtime of a known site "
  site = SITES[cmd_in.group(1)]
  if site['atime'] <= 0 :
    mesg = "%s hasn't been checked yet" % (site['name'])
  elif site['mtime'] <= 0 :
    mesg = "%s latest update couldn't be fetched" % (site['name'])
  else:
    when_ago = _secsToPretty(site['mtime'])
    mesg = "%s updated %s" % (site['name'], when_ago)
  phenny.say(mesg)

tell_last_update.commands = SITES.keys()
tell_last_update.thread = False  # don't bother, non-blocking
