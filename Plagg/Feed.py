# Feed.py -- one configured feed

# $Id$

import sys, os, re, urllib2
import feedparser	# needs at least version 3 beta 22!
import Plagg		# for default encoding

from httpcache import HTTPCache

USER_AGENT = 'plagg/%s (+http://www.drbeat.li/py/plagg/)' % Plagg.__tarversion__


class Feed:
    """Abstract Feed class.
    Knows its name and URI, <outline> attributes and feedparser dict."""

    def __init__(self, attrs, name, uri):
	self.attrs = attrs
	self.name = name
	self.uri = uri
	self.headers = {'User-Agent': USER_AGENT}
	self.feed = {}
	self.linkReplacements = []	# lists of (re, new) tuples
	self.bodyReplacements = []
        self.encoding = Plagg.ENCODING

	# enable feedparser debugging
	if Plagg.VERBOSE > 2:
	    feedparser._debug = 1

    def getFeed(self):
	"""Sets self.feed to a feedparser dictionary. Subclasses must implement this."""
	raise NotImplementedError('Feed.getFeed()')

    def addLinkReplacement(self, old, new):
	if old:
	    self.linkReplacements.append((re.compile(old), new))

    def addBodyReplacement(self, old, new):
	if old:
	    self.bodyReplacements.append((re.compile(old), new))

    def replaceLink(self, link):
	return self.replaceText(link, self.linkReplacements)

    def replaceBody(self, body):
	return self.replaceText(body, self.bodyReplacements)

    def replaceText(self, text, repl):
	"""Performs a regex replacement according to the repl list."""
	for pattern, new in repl:
	    text = pattern.sub(new, text)
	return text


class RSSFeed(Feed):

    def getFeed(self):
	"""Builds an ultra-liberally parsed feed dict from the URL."""
	rss = HTTPCache(self.uri, self.headers)
	if not rss.fresh():
	    self.feed = feedparser.parse(rss.content())


class SimulatedFeed(Feed):
    """Simulates a feed by providing a template of an RSS 2.0 feed with
    one entry. Is used by subclasses which know how to get an item from
    a website."""

    RSS_TEMPLATE = u"""\
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

    def __init__(self, attrs, name, uri):
	Feed.__init__(self, attrs, name, uri)
	self.itemLink = ''
	self.itemTitle = ''
	self.itemBody = ''

    def generateFeed(self):
	if self.itemBody and not self.itemBody.startswith('<'):
	    self.itemBody = '<p>' + self.itemBody + '</p>'
	self.itemBody = Plagg.decode(self.itemBody)
	rss = self.RSS_TEMPLATE % self.__dict__
	rss = Plagg.encode(rss)
	self.feed = feedparser.parse(rss)


class HTMLFeed(SimulatedFeed):
    """Extracts a single link from a HTML page and builds an ad-hoc feed
    object from it.

    self.regex must contain one to three named groups. The group 'link' returns
    the extracted link, the optional group 'title' contains the item title, the
    third group 'body' returns the entry's body text. All relative links will
    already have been converted to absolute, and img tags will end with " />"."""

    def __init__(self, attrs, name, uri, regex):
	SimulatedFeed.__init__(self, attrs, name, uri)
	self.regex = re.compile(regex, re.I)

    def getLink(self):
	"""Reads the HTML page and extracts the link and title."""
	html = HTTPCache(self.uri, self.headers).content()#.decode(self.encoding)
	# resolve relative URIs
	html = feedparser._resolveRelativeURIs(html, self.uri, self.encoding)
	# search for the regex
	m = self.regex.search(html)
	if m:
	    try:
		if m.groupdict():	# new-style named groups regex
		    self.itemLink = m.group('link')
		    self.itemTitle = m.group('title')
		    if m.group('body'):
			# strip whitespace inside href attributes (for APOD)
			self.itemBody = re.sub(r'''(?s)href=(['"]).+?\1''',	# "
			    lambda m: re.sub(r'\s+', '', m.group(0)),
			    m.group('body')
			)
		else:			# old-style numbered groups
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
	    return

	# If the savepath and saveurl attributes are present,
	# save the linked-to item and adjust the itemLink to
	# point to the local copy. Allow to fake the referrer
	# while getting the remote file.
	if self.attrs.get('savepath') and self.attrs.get('saveurl'):
	    link = self.replaceLink(self.itemLink)
	    self.linkReplacements = []
	    basename = re.search('([^/]+)$', link).group(1)
	    localfile = os.path.join(self.attrs['savepath'], basename)
	    # only get and save the file if it doesn't exist yet
	    if not os.path.isfile(localfile):
		req = urllib2.Request(link)
		req.add_header('Referer', self.attrs.get('referrer') or self.uri or link)
		image = urllib2.urlopen(req).read()
		f = file(localfile, 'wb')
		f.write(image)
		f.close()
	    # adjust the itemLink in every case
	    self.itemLink = self.attrs['saveurl'] + '/' + basename

	self.generateFeed()


class ComputedFeed(HTMLFeed):
    """Builds the itemLink out of arbitrary Python statements."""

    def __init__(self, attrs, name, uri, suite):
	SimulatedFeed.__init__(self, attrs, name, uri)
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
