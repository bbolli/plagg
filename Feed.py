# Feed.py -- one configured feed

import re, socket, urllib2
import feedparser

# hide differences between version 2 and 3 of feedparser
try:
    feedparser._resolveRelativeURIs
except NameError:
    # version 2
    feedparser._resolveRelativeURIs = feedparser.resolveRelativeURIs


class Feed:
    """Abstract Feed class.
    Knows its name and URI.
    Can build a Blosxom entry from a feedparser object."""

    def __init__(self, name, uri):
	self.name = name
	self.uri = uri

    def getFeed(self):
	"""Returns a feedparser dictionary. Subclasses must implement this."""
	raise NotImplementedError('Feed.getFeed()')


class RSSFeed(Feed):

    def getFeed(self):
	"""Builds an ultra-liberally parsed feed object from the URL."""
	try:
	    return feedparser.parse(self.uri)
	except socket.timeout:
	    return None


class HTMLFeed(Feed):
    """Extracts a single link from a HTML page and builds an ad-hoc feed
    object from it.

    self.regex must contain one or two groups. The first group returns the 
    extracted link, the optional second group contains the item title. All 
    relative links will already have been converted to absolute."""

    RSS_TEMPLATE = """\
<?xml version="1.0" encoding="iso-8859-1"?>

<rss version="2.0">
  <channel>
    <title>%(name)s</title>
    <link>%(uri)s</link>
    <item>
      <title>%(itemTitle)s</title>
      <description>&lt;img src="%(itemLink)s" /&gt;</description>
    </item>
  </channel>
</rss>"""

    def __init__(self, name, uri, regex):
	Feed.__init__(self, name, uri)
	self.regex = re.compile(regex, re.I + 0*re.M)
	self.itemLink = ''
	self.itemTitle = ''

    def getLink(self):
	"""Reads the HTML page and extracts the link and title."""
	try:
	    f = urllib2.urlopen(self.uri)
	    html = f.read().decode('iso-8859-1')
	except socket.timeout:
	    return
	# resolve relative URIs
	html = feedparser._resolveRelativeURIs(html, self.uri)
	m = self.regex.search(html)
	if m:
	    self.itemLink = m.group(1)
	    if m.group(2):
		self.itemTitle = m.group(2)

    def getFeed(self):
	self.getLink()
	if not self.itemLink:
	    return None
	rss = self.RSS_TEMPLATE % self.__dict__
	return feedparser.parse(rss)


class HTMLSubstituteFeed(HTMLFeed):

    def __init__(self, name, uri, regex, old, new):
	HTMLFeed.__init__(self, name, uri, regex)
	self.old = old
	self.new = new

    def getLink(self):
	HTMLFeed.getLink(self)
	self.itemLink = self.itemLink.replace(self.old, self.new)
