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

    def __init__(self, opmlfile, newspath, nick=None):
	self.opmlfile = opmlfile
	self.newspath = newspath
	self.nick = nick
	self.logging = self.errors = self.entries = 0
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
	name = attrs.get('text')
	if not name: return
	nick = attrs.get('nick', name.lower())

	# select by nickname
	if self.nick and nick != self.nick: return

	# observe hours (in UTC!) unless a single feed is requested
	hours = attrs.get('hours')
	if hours and not self.nick and not _matchHours(hours, time.gmtime()[3]):
	    return

	# create a Feed instance based on the OPML type attribute
	kind = attrs.get('type', 'rss').lower()
	if kind == 'rss':
	    uri = attrs.get('xmlurl')
	    if not uri: return
	    feed = Feed.RSSFeed(attrs, name, uri)
	elif kind == 'x-bb-html':
	    uri, regex = attrs.get('link'), attrs.get('regex')
	    if not uri or not regex: return
	    feed = Feed.HTMLFeed(attrs, name, uri, regex)
	elif kind == 'x-bb-suite':
	    uri, suite = attrs.get('link'), attrs.get('suite')
	    if not suite: return
	    feed = Feed.SuiteFeed(attrs, name, uri, suite)
	else:
	    return

	# get and process this feed
	try:
	    feed.getFeed()
	except Exception, e:
	    sys.stderr.write("Feed: %s (%s)\n%s\n" % (feed.name, feed.uri, str(e)))
	    self.errors += 1
	    return
	if self.logging > 1:
	    print feed.feed
	e = Entries.BlosxomEntries(os.path.join(self.newspath, nick))
	e.logging = self.logging
	self.entries += e.processFeed(feed)
