# Feed.py -- one configured feed

# $Id: Feed.py 1074 2010-01-07 19:42:21Z bb $

import sys, os, re, socket, urllib2, pickle, hashlib
import feedparser	# needs at least version 3 beta 22!
import Plagg

USER_AGENT = 'plagg/%s (+http://drbeat.li/py/plagg/)' % Plagg.__tarversion__
CACHE_DIR = '.cache'

# set a global socket timeout of 20s
if hasattr(socket, 'setdefaulttimeout'):
    socket.setdefaulttimeout(20)


class Feed:
    """Abstract Feed class.
    Knows its name and URI, <outline> attributes and feedparser dict."""

    def __init__(self, attrs, name, uri):
	self.attrs = attrs
	self.name = name
	self.uri = uri
	self.headers = {'User-Agent': USER_AGENT}
	self.feed = {}
	self.replacements = []	# list of (what, re, new) tuples
	self.encoding = Plagg.ENCODING

	digest = hashlib.md5(self.uri).hexdigest()
	self.cachefile = os.path.join(CACHE_DIR, digest)
	self.etag = None
	self.modified = None

	# enable feedparser debugging
	if Plagg.VERBOSE > 2:
	    feedparser._debug = 1

    def getFeed(self):
	"""Sets self.feed to a feedparser dictionary. Subclasses must implement this."""
	raise NotImplementedError('Feed.getFeed()')

    def addReplacement(self, what, old, new):
	if what and old:
	    self.replacements.append((what, re.compile(old), new))

    def replaceText(self, what, text):
	"""Performs a regex replacement according to the list."""
	for pattern, new in [r[1:] for r in self.replacements if r[0] == what]:
	    text = pattern.sub(new, text)
	return text

    def loadCache(self):
	try:
	    _uri, self.etag, self.modified = pickle.load(open(self.cachefile))
	except Exception, e:
	    self.etag = self.modified = None

    def saveCache(self, etag, mod):
	try:
	    if not os.path.isdir(CACHE_DIR):
		os.makedirs(CACHE_DIR)
	    # the URI is saved just for reference
	    pickle.dump((self.uri, etag, mod), open(self.cachefile, 'w'))
	except Exception, e:
	    try:
		os.unlink(self.cacheFile)
	    except:
		pass


class RSSFeed(Feed):

    def getFeed(self):
	"""Builds an ultra-liberally parsed feed dict from the URL."""
	self.loadCache()
	feed = feedparser.parse(self.uri, etag=self.etag, modified=self.modified, agent=USER_AGENT)
	if feed.get('status') == 304:
	    # feed not modified
	    return
	self.feed = feed
	self.saveCache(feed.get('etag'), feed.get('modified'))


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
	self.loadCache()
	try:
	    f = feedparser._open_resource(self.uri, self.etag, self.modified, USER_AGENT, None, [])
	    html = f.read()
	except Exception, e:
	    sys.stderr.write('Getting page %s: %s\n' % (self.uri, e))
	    return

	if hasattr(f, 'status') and f.status == 304 \
	or not html:	# not modified or empty page
	    return

	# save HTTP headers
	if hasattr(f, 'info'):
	    info = f.info()
	    etag = info.getheader('ETag')
	    modified = info.getheader('Last-Modified')
	    if modified:
		modified = feedparser._parse_date(modified)
	    self.saveCache(etag, modified)

	    # if the page is compressed, decompress it
	    ce = info.getheader('Content-Encoding', '')
	    if ce == 'gzip':
		try:
		    import gzip, StringIO
		    html = gzip.GzipFile(fileobj=StringIO.StringIO(html)).read()
		except Exception, e:
		    sys.stderr.write('Unzipping page %s: %s\n' % (self.uri, e))
		    return
	    elif ce == 'deflate':
		try:
		    import zlib
		    html = zlib.decompress(html, -zlib.MAX_WBITS)
		except Exception, e:
		    sys.stderr.write('Inflating page %s: %s\n' % (self.uri, e))
		    return

	# resolve relative URIs
	html = feedparser._resolveRelativeURIs(html, self.uri, self.encoding)

        if hasattr(f, 'headers'):
            charsets = [c for c in feedparser._getCharacterEncoding(f.headers, html) if c]
        else:
            charsets = [self.encoding]
        for charset in charsets:
            try:
                html = html.decode(charset)
                break
            except LookupError:
                pass

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
	    sys.stderr.write((u"Regex '%s' not found at %s:\n\n----\n%s----\n" % (
		self.regex.pattern, self.uri, html
	    )).encode(self.encoding))

    def getFeed(self):
	self.getLink()
	if not self.itemLink:
	    return

	# If the savepath and saveurl attributes are present,
	# save the linked-to item and adjust the itemLink to
	# point to the local copy. Allow to fake the referrer
	# while getting the remote file.
	if self.attrs.get('savepath') and self.attrs.get('saveurl'):
	    link = self.replaceText('link', self.itemLink)
	    self.replacements = [r for r in self.replacements if r[0] != 'link']
	    basename = re.search('([^/]+)$', link).group(1)
	    localfile = os.path.join(self.attrs['savepath'], basename)
	    # only get and save the file if it doesn't exist yet
	    if not os.path.isfile(localfile):
		req = urllib2.Request(link)
		req.add_header('Referer', self.attrs.get('referrer') or self.uri or self.itemLink)
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
	    self.itemTitle = re.search('([^/]+)(?:\.\w+)?$', self.itemLink).group(1)
