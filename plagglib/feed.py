"""feed.py -- one configured feed"""

import collections
import hashlib
import os
import pickle
import re
import socket
import sys
import urllib.request, urllib.error, urllib.parse
import xml.etree.ElementTree as et

import feedparser  # needs at least version 3 beta 22!

from . import plagg

USER_AGENT = f'plagg/{plagg.__version__} (+https://drbeat.li/py/plagg/)'

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
        self.headers = {}
        self.feed = {}
        self.replacements = collections.defaultdict(list)  # {what: [(old_re, new), ...]}
        self.encoding = plagg.ENCODING
        self.skip = {}

        digest = hashlib.md5(self.uri.encode()).hexdigest()
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
        elif name == 'header':
            self.addHeader(attrs.get('name'), attrs.get('value'))
        elif name == 'skip':
            self.skip = dict((k, re.compile(v)) for k, v in attrs.items())
        else:
            # default: do as if it were an <outline> attribute
            self.attrs[name] = content

    def addReplacement(self, what, old, new):
        if what and old:
            self.replacements[what].append((re.compile(old), new))

    def replaceText(self, what, text):
        """Performs a regex replacement according to the list."""
        for pattern, new in self.replacements[what]:
            text = pattern.sub(new, text)
        return text

    def skipEntry(self, what, text):
        return what in self.skip and self.skip[what].match(text)

    def addHeader(self, name, value):
        if name and value is not None:
            self.headers[name] = value

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
        feed = feedparser.parse(self.uri, etag=self.etag,
            modified=self.modified, agent=USER_AGENT,
            request_headers=self.headers
        )
        if feed.get('status') == 304:
            # feed not modified
            return
        self.feed = feed
        self.saveCache(feed.get('etag'), feed.get('modified'))


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
        self.item = self.iframe or f'<p><img src="{self.imgLink}" /></p>'
        if self.itemBody and not self.itemBody.startswith('<'):
            self.itemBody = f'<p>{self.itemBody}</p>'
        rss = self.RSS_TEMPLATE % self.__dict__
        self.feed = feedparser.parse(rss)


class HTMLFeed(SimulatedFeed):
    """Extracts a link or iframe from a HTML page and builds an ad-hoc feed
    object from it.

    There are two ways of matching the HTML content: by regex or by XPath."""

    children = frozenset(('regex', 'image-xpath', 'iframe-xpath'))

    def getLink(self):
        """Reads the HTML page and extracts the link, title and body."""

        if not self.children.intersection(self.attrs):
            return      # mandatory child element missing

        self.loadCache()
        resp = {}
        try:
            html = feedparser.api._open_resource(self.uri, self.etag, self.modified,
                USER_AGENT, None, [], self.headers, resp
            ).read()
        except Exception as e:
            print(f'Getting page {self.uri}: {e}', file=sys.stderr)
            return

        if resp['status'] == 304 or not html:
            # not modified or empty page
            return

        self.saveCache(resp.get('etag'), resp.get('modified_parsed'))

        html = feedparser.encodings.convert_to_utf8(resp['headers'], html, resp).decode('utf-8')
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
                groups = m.groupdict()
                if groups:      # new-style named groups regex
                    self.imgLink = groups.get('link')
                    relLink = groups.get('rellink')
                    # handle relative links
                    if not self.imgLink and relLink:
                        self.imgLink = self.uri + relLink
                    self.iframe = groups.get('iframe')
                    self.itemTitle = groups.get('title')
                    # strip whitespace inside href attributes (for APOD)
                    self.itemBody = re.sub(r'''(?s)href=(['"]).+?\1''',
                        lambda m: re.sub(r'\s+', '', m.group(0)),
                        groups.get('body', '')
                    )
                else:                   # old-style numbered groups
                    self.imgLink = m.group(1)
                    self.itemTitle = m.group(2)
                # run the link replacements
                self.imgLink = self.replaceText('link', self.imgLink)
            except IndexError:
                pass
        else:
            print(f"Regex '{regex}' not found at {self.uri}:\n\n----\n{html}----",
                file=sys.stderr
            )

    def match_xpath(self, html):
        """Search for the content given by the {image,title,body,iframe}-xpath values."""

        # remove scripts; they generally can't be parsed as XML
        html = script_re.sub('', html)

        # Replace entity references by their corresponding character references.
        from html.entities import name2codepoint
        eref_re = re.compile('&(' + '|'.join(name2codepoint.keys()) + ');')
        html = eref_re.sub(lambda m: f'&#{name2codepoint[m.group(1)]}', html)

        try:
            root = et.fromstring(html)
        except Exception as e:
            print(f"Page at {self.uri} not parseable as XML: {e}\n\n----\n{html}----",
                file=sys.stderr
            )
            return

        def _find(attrname):
            if attrname not in self.attrs:
                return None
            xpath = self.attrs[attrname]
            # handle text and attribute access which are not done by ElementTree
            accessf = lambda e: et.tostring(e)  # default: element as X(HT)ML
            if xpath.endswith('/text()'):       # text content
                xpath = xpath[:-7]
                accessf = lambda e: e.text
            elif '/@' in xpath:                 # attribute value
                xpath, attrname = xpath.split('/@', 1)
                accessf = lambda e: e.get(attrname)
            for e in root.iterfind('.' + xpath):
                return accessf(e)               # use only the first match
            print(f"{attrname} '{xpath}' not found at {self.uri}:\n\n----\n{html}----",
                file=sys.stderr
            )

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
                req = urllib.request.Request(link)
                req.add_header('Referer', self.attrs.get('referrer') or self.uri or self.imgLink)
                image = urllib.request.urlopen(req).read()
                with file(localfile, 'wb') as f:
                    f.write(image)
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
            exec(self.suite)
        except Exception as e:
            print(f"{e} in suite\n\n----\n{self.suite}\n----", file=sys.stderr)
            self.imgLink = ''
            return
        if not self.itemTitle:
            self.itemTitle = re.search('([^/]+)(?:\.\w+)?$', self.imgLink).group(1)
