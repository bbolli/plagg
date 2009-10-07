"""Reads an OPML file, gets all feeds in it and writes Blosxom entries
corresponding to the items in the feeds."""

# $Id$

import os, sys, time, xml.sax, httplib

__version__ = "1.8 ($Id$)"
w = __version__.split()
__tarversion__ = w[0] + '.' + w[3]
del w

import Feed, Entries

ENCODING = 'utf-8'	# default character encoding, used by Feed.py and Entries.py

VERBOSE = 0             # will be set by Plagg.setLogging()

def encode(text):
    """Converts a unicode string to its encoded equivalent."""
    if isinstance(text, unicode):
	return text.encode(ENCODING, 'xmlcharrefreplace')
    return text

def decode(text):
    """Converts a string to its unicode equivalent."""
    if isinstance(text, str):
	text = unicode(text, ENCODING, 'replace')
    return text


def _matchHours(hours, currentHour):
    """Returns true if currentHour is present in hours.
    hours is a comma-separated list of ranges or single hour numbers,
    e.g. 0-5,12,17 or 0,1,3-9,14-18. currentHour is in 24-hour (military)
    format."""
    for r in hours.split(','):
	try:
	    h = [int(part) for part in r.split('-')]
	except ValueError:	# catch failing string to int conversions
	    continue
	if len(h) == 2 and h[0] <= currentHour <= h[1] \
	or len(h) == 1 and h[0] == currentHour:
	    return True
    return False


class Plagg(xml.sax.handler.ContentHandler):
    """The application class. Generates entries from each feed in the OPML file."""

    def __init__(self, opmlfile, newspath, nicks=None):
	self.opmlfile = opmlfile
	self.newspath = newspath
	self.nicks = nicks
	self.logging = self.errors = 0
	self.newentries = {}
	self.feed = None
	xml.sax.handler.ContentHandler.__init__(self)

    def setLogging(self, logging):
        global VERBOSE
        VERBOSE = logging

    def startOPML(self):
	xml.sax.parse(self.opmlfile, self)

    def startElement(self, name, attrs):
	if name == 'outline':
	    # Normalize attribute names to lower case
	    self.outline(dict([(k.lower(), v) for k, v in attrs.items()]))
	elif self.feed:
	    if name == 'replaceBody':
		self.feed.addBodyReplacement(attrs.get('from'), attrs.get('to', ''))
	    elif name == 'replaceLink':
		self.feed.addLinkReplacement(attrs.get('from'), attrs.get('to', ''))

    def endElement(self, name):
	"""Ends one outline element by processing the feed."""
	if name != 'outline' or not self.feed: return

	# process the feed
	e = Entries.BlosxomEntries(self, self.path)
	e.logging = VERBOSE
	e.processFeed(self.feed)

    def outline(self, attrs):
	"""Handles one OPML outline element."""

	# reset the feed dict
	self.feed = None

	# get common attributes
	name = attrs.get('text') or attrs.get('title')
	if not name: return
	nick = attrs.get('nick', name.lower())

	# select by nickname
	if self.nicks and not nick in self.nicks: return

	# observe hours (in UTC!) unless only some feeds are requested
	hours = attrs.get('hours')
	if hours and not self.nicks and not _matchHours(hours, time.gmtime()[3]):
	    return

	# create a Feed instance based on the OPML type attribute
	kind = attrs.get('type', 'rss').lower()
	if kind == 'rss':
	    uri = attrs.get('xmlurl')
	    if not uri: return
	    feed = Feed.RSSFeed(attrs, name, uri)
	elif kind == 'x-plagg-html':
	    uri, regex = attrs.get('htmlurl'), attrs.get('regex')
	    if not uri or not regex: return
	    feed = Feed.HTMLFeed(attrs, name, uri, regex)
	elif kind == 'x-plagg-computed':
	    uri, suite = attrs.get('htmlurl'), attrs.get('commands')
	    if not suite: return
	    feed = Feed.ComputedFeed(attrs, name, uri, suite)
	else:
	    return

	# get this feed
	try:
	    feed.getFeed()
	except httplib.HTTPException, e:
	    sys.stderr.write(("Feed: %s (%s): %s\n" % (feed.name, feed.uri, e.__class__.__name__)).encode(ENCODING, 'replace'))
	except Exception, e:
	    import traceback
	    if VERBOSE > 1:
		sys.stderr.write("Feed: %s (%s)\n" % (feed.name.encode(ENCODING, 'replace'), feed.uri))
		traceback.print_exc()
		self.errors += 1
	    else:
		e_str = str(e).lower()
		for msg in (
		    'timed out', 'connection refused', 'reset by peer',
		    'name resolution', 'no route'
		):
		    if e_str.find(msg) >= 0:
			break
		else:
		    sys.stderr.write(("Feed: %s (%s)\n%s: %s\n" % (feed.name, feed.uri, e.__class__.__name__, e)).encode(ENCODING, 'replace'))
		    self.errors += 1
	    return

	if VERBOSE > 2:
	    import pprint
	    pprint.pprint(feed.feed)
	    if 'bozo_exception' in feed.feed:
		print feed.feed['bozo_exception']

	self.feed = feed
	self.path = os.path.join(self.newspath, nick)

    def newEntry(self, entry):
	if entry._title:
	    self.newentries.setdefault(entry.newKey(), []).append(entry)

    def newEntries(self):
	body = []
	for c in self.newentries.keys():
	    body.append('* ' + c)
	    for e in self.newentries[c]:
		body.append('** %s' % e.newSummary())
	if body:
	    e = Entries.Entry()
	    e.setEntry('Latest news (%s)' % time.strftime('%H:%M:%S'), u'\n'.join(body))
	    e.setMeta(markup='textile2')
	    e.write(self.newspath, '.txt', overwrite=True, fname='Latest')
