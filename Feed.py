# Feed.py -- one configured feed

# $Id$

import sys, re, socket, urllib2

import feedparser	# use at least version 3 beta 22!
feedparser.USER_AGENT = 'plagg/$Rev$ ' + feedparser.USER_AGENT
#feedparser._debug = 1

import Plagg		# for default encoding

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
	except (socket.timeout, UnicodeDecodeError), e:
	    sys.stderr.write("Feed: %s (%s)\n%s\n" % (self.name, self.uri, e))


class HTMLFeed(Feed):
    """Extracts a single link from a HTML page and builds an ad-hoc feed
    object from it.

    self.regex must contain one to three named groups. The group 'link' returns
    the extracted link, the optional group 'title' contains the item title, the
    third group 'body' returns the entry's body text. All relative links will
    already have been converted to absolute."""

    RSS_TEMPLATE = """\
<?xml version="1.0" encoding="%(encoding)s"?>

<rss version="2.0">
  <channel>
    <title>%(name)s</title>
    <link>%(uri)s</link>
    <item>
      <title>%(itemTitle)s</title>
      <description><p><img src="%(itemLink)s" /></p>%(itemBody)s</description>
    </item>
  </channel>
</rss>"""

    def __init__(self, name, uri, regex):
	Feed.__init__(self, name, uri)
	self.regex = re.compile(regex, re.I)
	self.itemLink = ''
	self.itemTitle = ''
	self.itemBody = ''
	self.encoding = Plagg.ENCODING

    def getLink(self):
	"""Reads the HTML page and extracts the link and title."""
	try:
	    f = urllib2.urlopen(self.uri)
	    html = f.read().decode(self.encoding)
	except socket.timeout:
	    return
	# resolve relative URIs
	html = feedparser._resolveRelativeURIs(html, self.uri, self.encoding)
	m = self.regex.search(html)
	if m:
	    try:
		if m.groupdict():	# new-style group names in regex
		    self.itemLink = m.group('link')
		    self.itemTitle = m.group('title')
		    self.itemBody = '<p>' + m.group('body') + '</p>'
		else:
		    self.itemLink = m.group(1)
		    self.itemTitle = m.group(2)
	    except IndexError:
		pass

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
