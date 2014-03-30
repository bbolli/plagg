"""feed.py -- one configured feed"""

import sys, os, re, socket, urllib2, pickle, hashlib
import xml.etree.ElementTree as et
import feedparser	# needs at least version 3 beta 22!
import plagg

USER_AGENT = 'plagg/%s (+http://drbeat.li/py/plagg/)' % plagg.__version__

try:
    CACHE_DIR = [os.environ['XDG_CACHE_HOME']]
except KeyError:
    CACHE_DIR = [os.path.expanduser('~'), '.cache']
CACHE_DIR.append('plagg')
CACHE_DIR = os.path.join(*CACHE_DIR)

# set a global socket timeout of 20s
if hasattr(socket, 'setdefaulttimeout'):
    socket.setdefaulttimeout(20)

# feedparser shouldn't filter <iframe> and HTML5 elements
try:
    feedparser._HTMLSanitizer.acceptable_elements.add('iframe')
    feedparser._HTMLSanitizer.acceptable_elements.add('article')
    feedparser._HTMLSanitizer.acceptable_elements.add('section')
    feedparser._HTMLSanitizer.acceptable_elements.add('header')
    feedparser._HTMLSanitizer.acceptable_elements.add('footer')
    feedparser._HTMLSanitizer.acceptable_elements.add('aside')
    feedparser._HTMLSanitizer.acceptable_elements.add('audio')
    feedparser._HTMLSanitizer.acceptable_elements.add('video')
except:
    pass

# regex to strip scripts from a page
script_re = re.compile(r'(?is)<script.*?</script>')


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
	self.encoding = plagg.ENCODING

	digest = hashlib.md5(self.uri).hexdigest()
	self.cachefile = os.path.join(CACHE_DIR, digest)
	self.etag = None
	self.modified = None
	self.use_cache = True

	# enable feedparser debugging
	if plagg.VERBOSE > 2:
	    feedparser._debug = 1

    def addChildElement(self, name, attrs, content):
	"""Handle an <outline> child element"""
	if name == 'replace':
	    self.addReplacement(attrs.get('what'), attrs.get('from'), attrs.get('to', ''))
	else:
	    # default: do as if it were an <outline> attribute
	    self.attrs[name] = content

    def addReplacement(self, what, old, new):
	if what and old:
	    self.replacements.append((what, re.compile(old), new))

    def replaceText(self, what, text):
	"""Performs a regex replacement according to the list."""
	for pattern, new in [r[1:] for r in self.replacements if r[0] == what]:
	    text = pattern.sub(new, text)
	return text

    def getFeed(self):
	"""Sets self.feed to a feedparser dictionary. Subclasses must implement this."""
	raise NotImplementedError('Feed.getFeed()')

    def loadCache(self):
	if not self.use_cache:
	    return
	try:
	    _uri, self.etag, self.modified = pickle.load(open(self.cachefile))
	except Exception as e:
	    self.etag = self.modified = None

    def saveCache(self, etag, mod):
	if not self.use_cache:
	    return
	try:
	    if not os.path.isdir(CACHE_DIR):
		os.makedirs(CACHE_DIR)
	    # the URI is saved just for reference
	    pickle.dump((self.uri, etag, mod), open(self.cachefile, 'w'))
	except Exception as e:
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
      <description>%(item)s\n%(itemBody)s</description>
    </item>
  </channel>
</rss>"""

    def __init__(self, attrs, name, uri):
	Feed.__init__(self, attrs, name, uri)
	self.imgLink = ''
	self.iframe = ''
	self.itemTitle = ''
	self.itemBody = ''

    def generateFeed(self):
	self.item = self.iframe or '<p><img src="%s" /></p>' % self.imgLink
	if self.itemBody and not self.itemBody.startswith('<'):
	    self.itemBody = '<p>%s</p>' % self.itemBody
	self.itemBody = plagg.decode(self.itemBody)
	rss = self.RSS_TEMPLATE % self.__dict__
	rss = plagg.encode(rss)
	self.feed = feedparser.parse(rss)


class HTMLFeed(SimulatedFeed):
    """Extracts a link or iframe from a HTML page and builds an ad-hoc feed
    object from it.

    There are two ways of matching the HTML content: by regex or by XPath."""

    def getLink(self):
	"""Reads the HTML page and extracts the link, title and body."""

	for a in ('regex', 'image-xpath', 'iframe-xpath'):
	    if a in self.attrs:
		break
	else:
	    return	# mandatory child element missing

	self.loadCache()
	try:
	    f = feedparser._open_resource(self.uri, self.etag, self.modified, USER_AGENT, None, [], {})
	    html = f.read()
	except Exception as e:
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
		except Exception as e:
		    sys.stderr.write('Unzipping page %s: %s\n' % (self.uri, e))
		    return
	    elif ce == 'deflate':
		try:
		    import zlib
		    html = zlib.decompress(html, -zlib.MAX_WBITS)
		except Exception as e:
		    sys.stderr.write('Inflating page %s: %s\n' % (self.uri, e))
		    return

	# resolve relative URIs
	html = feedparser._resolveRelativeURIs(html, self.uri, self.encoding, 'text/html')

	if hasattr(f, 'headers'):
	    charsets = [c for c in feedparser._getCharacterEncoding(f.headers, html) if c]
	else:
	    charsets = [self.encoding]
	for charset in charsets:
	    try:
		html = html.decode(charset)
		break
	    except UnicodeDecodeError:
		pass
	    except LookupError:
		pass

	if 'regex' in self.attrs:
	    self.match_regex(html)
	else:
	    self.match_xpath(html)

    def match_regex(self, html):
	"""Search for the regex."""
	regex = self.attrs['regex']
	m = re.search(regex, html, re.I)
	if m:
	    try:
		if m.groupdict():	# new-style named groups regex
		    self.imgLink = m.group('link')
		    self.iframe = m.group('iframe')
		    self.itemTitle = m.group('title')
		    if m.group('body'):
			# strip whitespace inside href attributes (for APOD)
			self.itemBody = re.sub(r'''(?s)href=(['"]).+?\1''',	# "
			    lambda m: re.sub(r'\s+', '', m.group(0)),
			    m.group('body')
			)
		else:			# old-style numbered groups
		    self.imgLink = m.group(1)
		    self.itemTitle = m.group(2)
		# run the link replacements
		self.imgLink = self.replaceText('link', self.imgLink)
	    except IndexError:
		pass
	else:
	    sys.stderr.write((u"Regex '%s' not found at %s:\n\n----\n%s----\n" % (
		regex, self.uri, html
	    )).encode(self.encoding))

    def match_xpath(self, html):
	"""Search for the content given by the {image,title,body,iframe}-xpath values."""

	# remove scripts; they generally can't be parsed as XML
	html = script_re.sub('', html)
	try:
	    root = et.fromstring(html)
	except Exception as e:
	    sys.stderr.write(u"Page at %s not parseable as XML: %s\n" % (self.uri, e))
	    return

	def _find(attrname):
	    if attrname not in self.attrs: return None
	    xpath = self.attrs[attrname]
	    # handle text and attribute access which are not done by ElementTree
	    accessf = lambda e: et.tostring(e)	# default: element as X(HT)ML
	    if xpath.endswith('/text()'):	# text content
		xpath = xpath[:-7]
		accessf = lambda e: e.text
	    elif '/@' in xpath:			# attribute value
		xpath, attrname = xpath.split('/@', 1)
		accessf = lambda e: e.get(attrname)
	    for e in root.iterfind('.' + xpath):
		return accessf(e)		# use only the first match
	    sys.stderr.write((u"%s '%s' not found at %s:\n\n----\n%s----\n" % (
		attrname, xpath, self.uri, html
	    )).encode(self.encoding))

	self.imgLink = _find('image-xpath')
	self.itemTitle = _find('title-xpath')
	self.itemBody = _find('body-xpath')
	self.iframe = _find('iframe-xpath')

    def getFeed(self):
	self.getLink()
	if not self.imgLink and not self.iframe:
	    return

	# If the savepath and saveurl attributes are present,
	# save the linked-to item and adjust the imgLink to
	# point to the local copy. Allow to fake the referrer
	# while getting the remote file.
	if self.imgLink and self.attrs.get('savepath') and self.attrs.get('saveurl'):
	    basename = os.path.split(self.imgLink)[1]
	    localfile = os.path.join(self.attrs['savepath'], basename)
	    # only get and save the file if it doesn't exist yet
	    if not os.path.isfile(localfile):
		req = urllib2.Request(link)
		req.add_header('Referer', self.attrs.get('referrer') or self.uri or self.imgLink)
		image = urllib2.urlopen(req).read()
		f = file(localfile, 'wb')
		f.write(image)
		f.close()
	    # adjust the imgLink in every case
	    self.imgLink = self.attrs['saveurl'] + '/' + basename

	self.generateFeed()


class ComputedFeed(HTMLFeed):
    """Builds the imgLink out of arbitrary Python statements."""

    def __init__(self, attrs, name, uri, suite):
	SimulatedFeed.__init__(self, attrs, name, uri)
	self.suite = suite

    def getLink(self):
	"""Execute the suite which should set at least self.imgLink"""
	try:
	    exec self.suite
	except Exception as e:
	    sys.stderr.write("%s in suite\n\n----\n%s\n----\n" % (str(e), self.suite))
	    self.imgLink = ''
	    return
	if not self.itemTitle:
	    self.itemTitle = re.search('([^/]+)(?:\.\w+)?$', self.imgLink).group(1)
