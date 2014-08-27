"""
url_notify.py - Phenny module to check websites for updates
Rewritten again by Mozai
This is free and unencumbered software released into the public domain.
"""
# 2014-08-21 : removed the "raise Exception()" bits
#    because the owner-alert messages may be triggering anti-spam K-LINEs
#    this is bad Python style, but the alternative is the bot being banned
import email.utils, httplib, re, time, threading, urllib

# -- config
# global time between checks & min time between alerts
# any 'delay' setting in SITES less than this will be rounded up to this
LOOPDELAY = 30  # 30 seconds

# after an update, or an error, skip checking for this many seconds
FREEZEDELAY = 300  # 10 minutes

# timeout between command responses
# bots shouldn't spam, even when asked to
TELLDELAY = 60

# sites to check
# 'cmd' : {   used for '.cmd' to report last mtime
#  'name': used when reporting last mtime and in default mesg
#  'url': 'http://host/path/blah',
#  'url': ('starting url', regexp to next url, regexpt to next url, ...)
#  'method': 'last-modified' <- check HTTP header of final http request
#            'rss' <- check <channel><item>[0]<pubDate>
#            'atom' <- check <entry>[0]<published>
#            'last-url' <- compare found URL with prevous found URL
#            default is 'last-modified'
#  'delay': minimum seconds between checks,
#  'dest': (channels to announce, nicks to notify) ,
#          defaults to all channels bot was configured to join
#  'mesg': what to say when alerting. defaults to "\x02${name} has updated\x02"\
#          '%u' in the mesg will be replaced with current found URL
#  }

# SITES['url'] as a tuple could use more explanation.
#   if the 'url' field is a tuple, it will fetch the URL in [0],
#   apply the regexp in [1] to get a new url from the first parenthesized group,
#   repeat with the regexp in [n+1], etc, resulting in a final URL to use.
# SITES['last-url'] is used when it's enough to check the URL itself for changes
#   it is only useful if the ['url'] field is a tuple, explaned above.
#   otherwise, the resulting last URL will be checked for content as normal.

SITES = {
  'update': {
    'name': 'MSPA',
    'url': 'http://mspaintadventures.com/rss/rss.xml',
    'method': 'last-modified',
    'dest': '#farts',
    'mesg': '======= ======= UPDATE UPDATE ======= =======\n' +
            '======= http://mspaintadventures.com/ =======\n' +
            '======= ======= UPDATE UPDATE ======= =======\n'
  },
  'prequel': {
    'name': 'PREQUEL',
    'url': 'http://www.prequeladventure.com/feed/',
    'method': 'rss',
  },
  'sbahj': {
    'name': 'SBaHJ',
    'url': ('http://www.mspaintadventures.com/sweetbroandhellajeff/',
      r'="(.*?)"><img src="new.jpg"',
      r'<img src="(archive/.*?)"'),
    'method': 'last-url',
    'dest': '#farts',
    'mesg': '= JESUS \x02DICK\x02 ==================hornse==\n' +
      '=== THERSE A SWEET HELLA UPDTE ======-=\n'
  },
  'mspandrew': {
    'name': 'Hussie\'s tumblr',
    'url': 'http://mspandrew.tumblr.com/rss',
    'method': 'rss',
    'dest': '#farts'
  },
  'pxs': {
    'name': 'Paradox space',
    'url': 'http://paradoxspace.com/rss.atom',
    'dest': '#farts',
    'method': 'atom',
  },
  'demons': {
    'name': 'Kill Six Billion Demons',
    'url': 'http://killsixbilliondemons.com/?feed=rss2',
    'method': 'last-modified',
  },
  'sticky': {
    'name': 'HSG Sticky',
    'url': ('http://mspa.dumbgarbage.com/hsg/',
      r'<i class="fa fa-thumb-tack"></i><a href="(/hsg/res/\d+\.html)">'),
    'method': 'last-url',
    'dest': '#farts',
    'delay': 120,
    'mesg': 'New sticky at dumbgarbage'
  },
}

# --- end config

for SITE in SITES:
    # set defaults
    SITES[SITE]['mtime'] = 0
    SITES[SITE]['atime'] = 0
    SITES[SITE]['alert'] = False
    SITES[SITE]['error'] = None
    SITES[SITE]['last-url'] = None
    SITES[SITE].setdefault('name', SITE)
    SITES[SITE].setdefault('delay', LOOPDELAY)
    SITES[SITE].setdefault('method', 'last-modified')
    SITES[SITE].setdefault('mesg', "\x02%s has updated\x02" % SITES[SITE]['name'])
    if SITES[SITE]['method'] == 'last-url':
        if not isinstance(SITES[SITE]['url'], (list, tuple)):
            print '*** ERROR: site config mismatch: %s has method \'last-url\' but \'url\' is not a tuple' % SITE
            SITES[SITE]['error'] = 'config mismatch: method "last-url" but "url" is not tuple'
            SITES[SITE]['url'] = None  # prevent checking

ISO8601_re = re.compile(r'(\d\d\d\d)\-?(\d\d)\-?(\d\d)[T ]?(\d\d):?(\d\d):?(\d\d)(\.\d+)?([-+]\d\d(?::\d\d)?)?')


class OriginFake(object):
    """ this ugly piece of crap is so I can properly do exception
        the Phenny-way without annoying everyone on every channel """
    def __init__(self):
        self.sender = None  # the destination of the exception message


def _parsedate(dstring):
    " because people are inconsistent about their date strings "
    # The RSS 2.0 spec says 'use rfc822' (now RFC2822)
    dresult = email.utils.parsedate_tz(dstring)
    if dresult is not None:
        delta = dresult[9] * -1
        dresult = time.mktime(dresult[:9]) + delta  # to GMT
    elif dresult is None and ISO8601_re.match(dstring):
        # ...but the W3C says to use ISO8601, which has many valid strings
        # 2014-07-03T00:00:00-04:00
        match = ISO8601_re.match(dstring)
        dtuple = time.strptime(''.join(match.group(1, 2, 3, 4, 5, 6)), '%Y%m%d%H%M%S')
        dresult = time.mktime(dtuple)
        # now to parse timezone, put it to GMT
        delta = 0
        if match.group(8):
            delta = int(match.group(8)[1:3]) * (60 * 60)
            if len(match.group(8)) > 3:
                delta += int(match.group(8).replace(':', '')[3:5]) * 60
            if match.group(8)[0] == '-':
                delta *= -1
        dresult = dresult + delta
    else:
        print "ERR: unable to parse datestring \"%s\" % dstring"
        dresult = None
    # now go back from GMT to localtime
    dresult -= (time.daylight and time.altzone or time.timezone)
    return dresult


def notify_owner(phenny, mesg):
    " carp to bot's owner, not to the channel "
    if hasattr(phenny, 'bot'):
        phenny = phenny.bot
    # 2014-08-20: Rizon keeps hitting this bot with a k-line
    #   maybe because of frequently repeated messages
    #try:
    #    ownernick = phenny.config.owner
    #    phenny.msg(ownernick, mesg)
    #except AttributeError:
    #    # no owner configured? we carp to console anyways
    #    pass
    phenny.log('*** ' + mesg)


def _follow_url_chain(site):
    # sometimes the url config is (url, regexp, regexp, ...)
    url = site['url'][0]
    for step in site['url'][1:]:
        regexp = re.compile(step)
        (host, path) = urllib.splithost(urllib.splittype(url)[1])
        # using httplib so I can have 'timeout' that isn't in urllib.
        try:
            conn = httplib.HTTPConnection(host, timeout=3)
            conn.request('GET', path)
            response = conn.getresponse()
        except Exception as err:
            site['error'] = repr(err)
            print 'WARN: site %s get %s failed: %s' % (site['name'], url, repr(err))
            return None
        if response.status >= 300 and response.status < 400:
            site['url'] = None  # skip checking from now on
            site['error'] = 'HTTP response code %d' % response.status
            print 'ERR: site %s should use url %s' % (site['name'], response.getheader('Location'))
        match = regexp.search(response.read())
        conn.close()
        if match:
            url = urllib.basejoin(url, match.group(1))
        else:
            url = None
            break
    return url


def _update_siterecord(site):
    " update the SITES dict() if desired. may raise socket.timeout "
    # I packaged this into a seperate function to please pylint & PEP8
    # This isn't thread-safe; would be better to get a lock on SITES[site]
    # while I'm doing the update, but there *shouldn't* be multiple
    # threads checking URLs for update.  ... *shouldn't*
    # 2014 Aug: and now pylint wants me to break this up into multiple functions
    url = site['url']
    if url is None:
        # we marked this as so flawed we should stop checking
        return None
    now = time.mktime(time.localtime())  # now BEFORE check
    if site['atime'] + site['delay'] > now:
        # too soon to check again
        return None
    if site['mtime'] + FREEZEDELAY > now:
        # updated recently, wait a while
        return None
    if (site['error'] is not None) and (site['atime'] + FREEZEDELAY > now):
        # there's a problem, so check less often
        # print "INFO: not checking %s because: %s" % (site['name'], site['error'].replace("\n", " "))
        return None
    site['atime'] = now
    if isinstance(url, (list, tuple)):
        newurl = _follow_url_chain(site)
        if not newurl:
            site['error'] = "failed to follow url chain"
            print "WARN: site %s url chain failed" % (site['name'])
            return None
        if not site['last-url']:
            site['last-url'] = newurl
        if site['method'] == 'last-url' and newurl != site['last-url']:
            site['alert'] = True
        site['last-url'] = newurl
        url = newurl
    (host, path) = urllib.splithost(urllib.splittype(url)[1])
    try:
        connect = httplib.HTTPConnection(host, timeout=2)
        if site['method'] in ('rss', 'pubDate', 'atom', 'published'):
            connect.request("GET", path)
        else:
            connect.request("HEAD", path)
        response = connect.getresponse()
    except Exception as err:
        site['error'] = repr(err)
        print 'WARN: site %s head %s failed: %s' % (site['name'], url, repr(err))
        return None
    if response.status >= 300 and response.status < 400:
        site['url'] = None  # skip checking from now on
        site['error'] = "got HTTP response %d; removing from queue"
        print 'ERR: site %s should use url %s (%s)' % (site['name'], response.getheader('Location'), url)
        return None
    responsebody = response.read()
    if site['method'] in ('pubDate', 'rss'):
        mtime = re.search(r'<item>.*?<pubDate>(.*?)</pubDate>', responsebody, re.I | re.S)
        if mtime is not None and mtime.group(1) is not None:
            mtime = mtime.group(1)
            new_mtime = _parsedate(mtime)
    elif site['method'] in ('published', 'atom'):
        mtime = re.search(r'<entry>.*?<published>(.*?)</published>', responsebody, re.I | re.S)
        if mtime is not None:
            mtime = mtime.group(1)
    else:
        mtime = response.getheader('last-modified', None)
    if mtime is None:
        site['url'] = None  # skip checking from now on
        site['error'] = "could not find last-modified time"
        print 'ERR: site %s; did not detect last-modify time; url %s' % (site['name'], url)
        return None
    new_mtime = _parsedate(mtime)
    if new_mtime is None:
        site['url'] = None  # skip checking from now on
        site['error'] = "could not parse last-modify time: \"%s\"" % mtime
        print 'ERR: site %s; mtime not parsable: %s' % (site['name'], mtime)
        return None
    else:
        site['error'] = None
    now = time.mktime(time.localtime())  # now AFTER check
    site['atime'] = now
    if site['mtime'] == 0:
        # we haven't checked yet
        site['mtime'] = new_mtime
    if new_mtime != site['mtime'] and site['method'] != 'last-url':
        # this also catches it if the URL's Last-Modified jumped backwards
        site['alert'] = True
        site['mtime'] = new_mtime
    return url


def url_notify_loop(phenny):
    " update SITES cache; if they changed recently carp about it "
    my_thread_name = threading.current_thread().name
    while phenny.notify_threadname == my_thread_name:
        for sitekey in SITES:
            if not phenny.notify_threadname == my_thread_name:
                break
            try:
                site = SITES[sitekey]
                _update_siterecord(site)
                if site['alert']:
                    if 'dest' in site:
                        targets = site['dest']
                    else:
                        targets = phenny.channels
                    for dest in targets:
                        url = site.get('last-url', None) or site['url']
                        mesg = site['mesg']
                        mesg = mesg.replace('%u', url)
                        for line in mesg.split("\n"):
                            phenny.msg(dest, line)
                    site['alert'] = False  # alert no longer pending
            except:
                origin = OriginFake()
                origin.sender = phenny.config.owner
                phenny.error(origin)
        if phenny.notify_threadname == my_thread_name:
            time.sleep(LOOPDELAY)


def setup(phenny):
    " starts url_notify_loop() "
    # PhennyWrapper was such a bad idea; never saw the point.
    if hasattr(phenny, 'bot'):
        phenny = phenny.bot
    thr_args = (phenny,)
    thr = threading.Thread(target=url_notify_loop, args=thr_args)
    # The next line is ugly, but no other choice it seems.
    phenny.notify_threadname = thr.name
    thr.start()


def url_notify_stop(phenny, cmd_in):
    " clobbers a flag to make url_notify_loop commit sudoku "
    who = cmd_in.nick
    if cmd_in.admin:
        phenny.msg(who, 'stopping notify (%s)' % (phenny.bot.notify_threadname))
        phenny.bot.notify_threadname = None

url_notify_stop.commands = ['notifystop', 'stopnotify']


def url_notify_start(phenny, cmd_in):
    " re-runs setup() unless there's already a thread running "
    who = cmd_in.nick
    if not cmd_in.admin:
        return
    if phenny.bot.notify_threadname:
        phenny.msg(who, 'notify thread already running (%s)' % phenny.bot.notify_threadname)
    else:
        phenny.msg(who, 'restarting notify loop')
        setup(phenny.bot)

url_notify_start.commands = ['notifystart', 'startnotify']


def _secsToPretty(ticks=0):
    " given ticks as a duration in seconds, in human-friendly units "
    day, remain = divmod(ticks, (24 * 60 * 60))
    hour, remain = divmod(remain, (60 * 60))
    minute, second = divmod(remain, 60)
    if day > 0:
        return "%dd %dh" % (day, hour)
    elif hour > 0:
        return "%dh %dm" % (hour, minute)
    elif minute > 0:
        return "%dm %ds" % (minute, second)
    else:
        return "less than a minute"


def tell_last_update(phenny, cmd_in):
    " utters the last mtime of a known site "
    now = time.mktime(time.localtime())
    self = phenny.bot.variables['tell_last_update']
    who = cmd_in.nick
    site = SITES[cmd_in.group(1)]
    if site['atime'] <= 0:
        mesg = "%s hasn't been checked yet" % (site['name'])
    elif site['mtime'] <= 0:
        mesg = "%s latest update couldn't be fetched" % (site['name'])
    else:
        when_ago = _secsToPretty(now - site['mtime'])
        mesg = "%s updated %s ago" % (site['name'], when_ago)
        if site['method'] == 'last-url':
          mesg += " (%s)" % site['last-url']
    if (self.atime + TELLDELAY) <= now:
        phenny.say(mesg)
    else:
        phenny.msg(who, mesg)

tell_last_update.commands = SITES.keys()
tell_last_update.thread = False  # don't bother, non-blocking
tell_last_update.atime = 0


def dump_sites(phenny, cmd_in):
    " spews the SITES data structure to stdout for diagnostcs "
    if not (cmd_in.admin or cmd_in.owner):
        return None
    phenny.msg(cmd_in.nick, "dumping notify.py state info to stdout")
    for i in sorted(SITES):
        print "  --- %s ---" % i
        for j in sorted(SITES[i]):
            if not j:
                continue
            if j in ('atime', 'ctime', 'mtime'):
                print "    %s: %s" % (j, time.ctime(SITES[i][j]))
            else:
                print "    %s: %s" % (j, repr(SITES[i][j]))

dump_sites.commands = ('notify_dump',)
dump_sites.thread = False  # don't bother, non-blocking

if __name__ == '__main__':
    print "--- Testing phenny module"
    from phennytest import PhennyFake, CommandInputFake
    FAKEPHENNY = PhennyFake()
    FAKEPHENNY.variables['tell_last_update'] = tell_last_update
    for SITE in SITES:
        print "** %s **" % SITES[SITE]['name']
        _update_siterecord(SITES[SITE])
        FAKECMD = CommandInputFake('.%s' % SITE)
        tell_last_update(FAKEPHENNY, FAKECMD)
        print SITES[SITE]['url']
        print ""
