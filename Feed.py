# Feed.py -- one configured feed

# $Id$

import sys, os, re, socket, urllib2

import feedparser	# needs at least version 3 beta 22!
feedparser.USER_AGENT = 'plagg/%s ' % re.sub('\D', '', '$Rev$') + feedparser.USER_AGENT
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
	return feedparser.parse(self.uri)


class SimulatedFeed(Feed):
    """Simulates a feed by providing a template of an RSS 2.0 feed with
    one entry. Is used by subclasses which know how to get an item from
    a website."""

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

    def __init__(self, name, uri):
	Feed.__init__(self, name, uri)
	self.itemLink = ''
	self.itemTitle = ''
	self.itemBody = ''
	self.encoding = Plagg.ENCODING

    def generateFeed(self):
	rss = self.RSS_TEMPLATE % self.__dict__
	return feedparser.parse(rss)


class HTMLFeed(SimulatedFeed):
    """Extracts a single link from a HTML page and builds an ad-hoc feed
    object from it.

    self.regex must contain one to three named groups. The group 'link' returns
    the extracted link, the optional group 'title' contains the item title, the
    third group 'body' returns the entry's body text. All relative links will
    already have been converted to absolute, and img tags will end with " />"."""

    def __init__(self, name, uri, regex):
	SimulatedFeed.__init__(self, name, uri)
	self.regex = re.compile(regex, re.I)

    def getLink(self):
	"""Reads the HTML page and extracts the link and title."""
	f = urllib2.urlopen(self.uri)
	html = f.read().decode(self.encoding)
	# resolve relative URIs
	html = feedparser._resolveRelativeURIs(html, self.uri, self.encoding)
	# search for the regex
	m = self.regex.search(html)
	if m:
	    try:
		if m.groupdict():	# new-style group names in regex
		    self.itemLink = m.group('link')
		    self.itemTitle = m.group('title')
		    if m.group('body'):
			self.itemBody = '<p>' + m.group('body') + '</p>'
			# strip whitespace inside href attributes (for APOD)
			self.itemBody = re.sub(r'''(?s)href=(['"]).+?\1''',	# "
			    lambda m: re.sub(r'\s+', '', m.group(0)),
			    self.itemBody
			)
		else:
		    self.itemLink = m.group(1)
		    self.itemTitle = m.group(2)
	    except IndexError:
		pass
	else:
	    sys.stderr.write("Regex '%s' not found in page:\n\n----\n%s----\n" % (
		self.regex.pattern, html
	    ))

    def getFeed(self):
	self.getLink()
	if not self.itemLink:
	    return None

	# If the savepath and saveurl attributes are present,
	# save the linked-to item and adjust the itemLink to
	# point to the local copy. Allow to fake the referrer
	# while getting the remote file.
	attr = self.attrs.get
	if attr('savepath') and attr('saveurl'):
	    basename = re.search('([^/]+)$', self.itemLink).group(1)
	    localfile = os.path.join(attr('savepath'), basename)
	    # only get and save the file if it doesn't exist yet
	    if not os.path.isfile(localfile):
		req = urllib2.Request(self.itemLink)
		req.add_header('Referer', attr('referrer') or self.uri or self.itemLink)
		image = urllib2.urlopen(req).read()
		f = file(localfile, 'wb')
		f.write(image)
		f.close()
	    # adjust the itemLink in every case
	    self.itemLink = attr('saveurl') + '/' + basename

	return self.generateFeed()


class HTMLSubstituteFeed(HTMLFeed):
    """Same as class HTMLFeed, except that the item's link undergoes a
    string replacement."""

    def __init__(self, name, uri, regex, old, new):
	HTMLFeed.__init__(self, name, uri, regex)
	self.old = old
	self.new = new

    def getLink(self):
	HTMLFeed.getLink(self)
	self.itemLink = self.itemLink.replace(self.old, self.new)


class SuiteFeed(HTMLFeed):
    """Builds the itemLink out of an arbitrary Python statement suite."""

    def __init__(self, name, uri, suite):
	SimulatedFeed.__init__(self, name, uri)
	self.suite = suite

    def getLink(self):
        """Execute the suite which should set at least self.itemLink"""
    	try:
	    exec self.suite
	except Exception, e:
	    sys.stderr.write("%s in suite\n\n----\n%s\n----\n" % (str(e), self.suite))
	    self.itemLink = ''
	    return
	if not self.itemTitle:
	    self.itemTitle = re.search('([^/]+)(?:\.\w+)$', self.itemLink).group(1)
