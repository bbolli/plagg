"""Reads an OPML file, gets all feeds in it and writes Blosxom entries
corresponding to the items in the feeds."""

# $Id$

import os, sys, time, xml.sax

import Feed, Entries


ENCODING = 'iso8859_15'	# default character encoding, used by Feed.py and Entries.py


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
	xml.sax.handler.ContentHandler.__init__(self)

    def setLogging(self, logging):
	self.logging = logging

    def startOPML(self):
	xml.sax.parse(self.opmlfile, self)

    def startElement(self, name, attrs):
	if name == 'outline':
	    # Normalize attribute names to lower case
	    self.outline(dict([(k.lower(), v) for k, v in attrs.items()]))

    def outline(self, attrs):
	"""Handles one OPML outline element."""

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

	# get and process this feed
	try:
	    feed.getFeed()
	except Exception, e:
	    import traceback
	    if self.logging > 1:
		sys.stderr.write("Feed: %s (%s)\n" % (feed.name.encode(ENCODING, 'replace'), feed.uri))
		traceback.print_exc(file=sys.stderr)
		self.errors += 1
	    else:
		e_str = str(e).lower()
		if e_str.find('timed out') < 0 and e_str.find('connection refused') < 0:
		    sys.stderr.write("Feed: %s (%s)\n%s\n" % (feed.name.encode(ENCODING, 'replace'), feed.uri, e))
		    self.errors += 1
	    return
	if self.logging > 1:
	    print feed.feed
	e = Entries.BlosxomEntries(self, os.path.join(self.newspath, nick))
	e.logging = self.logging
	e.processFeed(feed)

    def newEntry(self, entry):
	if entry._title:
	    self.newentries.setdefault(entry.newKey(), []).append(entry)

    def newEntries(self):
	body = []
	for c in self.newentries.keys():
	    body.append('* ' + c)
	    for e in self.newentries[c]:
		body.append('** ' + e.newSummary())
	if body:
	    e = Entries.Entry()
	    e.setEntry('Latest news (%s)' % time.strftime('%H:%M:%S'), u'\n'.join(body))
	    e.setMeta(markup='textile2')
	    e.write(self.newspath, '.txt', overwrite=True, fname='Latest')
