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
	self.newspath = newspath
	self.nick = nick
	xml.sax.handler.ContentHandler.__init__(self)
	xml.sax.parse(opmlfile, self)

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
	    uri = attrs.get('xmlurl', '')
	    if not uri: return
	    feed = Feed.RSSFeed(name, uri)
	elif kind == 'x-bb-html':
	    uri, regex = attrs.get('link'), attrs.get('regex')
	    if not uri or not regex: return
	    old, new = attrs.get('from'), attrs.get('to')
	    if not old or new is None:
		feed = Feed.HTMLFeed(name, uri, regex)
	    else:
		feed = Feed.HTMLSubstituteFeed(name, uri, regex, old, new)
	elif kind == 'x-bb-suite':
	    uri, suite = attrs.get('link'), attrs.get('suite')
	    if not suite:
	        return
	    feed = Feed.SuiteFeed(name, uri, suite)
	else:
	    return

	# let the feed object know about the attribute dict
	feed.attrs = attrs

	# get and process this feed
	try:
	    f = feed.getFeed()
	except Exception, e:
	    sys.stderr.write("Feed: %s (%s)\n%s\n" % (feed.name, feed.uri, str(e)))
	    return
	e = Entries.BlosxomEntries(os.path.join(self.newspath, nick))
	e.processFeed(f)
