"""Reads an OPML file, gets all feeds in it and writes Blosxom entries
corresponding to the items in the feeds."""

from __future__ import with_statement

import httplib
import os
import pprint as _pprint
import sys
import threading
import time
import xml.sax

__version__ = "3.0"

from feed import RSSFeed, HTMLFeed, ComputedFeed
from entries import BlosxomEntries, Entry

ENCODING = 'utf-8'      # default character encoding, used by feed.py and entries.py

VERBOSE = 0             # will be set by Plagg.setConfig()
FOOTER = 1
OLD_ENTRIES = 0

pprint = None


def encode(text):
    """Converts a unicode string to its encoded equivalent."""
    if isinstance(text, unicode):
        return text.encode(ENCODING, 'xmlcharrefreplace')
    return text


def decode(text):
    """Converts a string to its unicode equivalent."""
    if isinstance(text, str):
        text = unicode(text, ENCODING, 'replace')
    return text


def _matchHours(hours, currentHour):
    """Returns true if currentHour is present in hours.
    hours is a comma-separated list of ranges or single hour numbers,
    e.g. 0-5,12,17 or 0,1,3-9,14-18. currentHour is in 24-hour (military)
    format."""
    for r in hours.split(','):
        try:
            h = [int(part) for part in r.split('-')]
        except ValueError:      # catch failing string to int conversions
            continue
        if len(h) == 2 and h[0] <= currentHour <= h[1]:
            return True
        if len(h) == 1 and h[0] == currentHour:
            return True
    return False


class Plagg(xml.sax.handler.ContentHandler):
    """The application class. Generates entries from each feed in the OPML file."""

    def __init__(self, opmlfile, nicks=None):
        self.opmlfile = opmlfile
        self.nicks = nicks
        self.logging = self.errors = 0
        self.newentries = []
        self.feed = None
        self.attrstack = []
        self.threads = []
        self.lock = threading.Lock()
        global pprint
        pprint = self.pprint
        xml.sax.handler.ContentHandler.__init__(self)

    def setConfig(self, newspath, logging, footer, old_entries):
        self.newspath = newspath
        global VERBOSE, FOOTER, OLD_ENTRIES
        VERBOSE = logging
        FOOTER = footer
        OLD_ENTRIES = old_entries

    def pprint(self, obj):
        with self.lock:
            if type(obj) in (str, unicode):
                print obj
            else:
                _pprint.pprint(obj)

    def startOPML(self):
        xml.sax.parse(self.opmlfile, self)
        for t in self.threads:
            t.join()

    def startElement(self, name, attrs):
        self.attrstack.append(attrs)
        if name == 'outline':
            self.feed = self.createFeed(attrs)
        self.content = ''

    def characters(self, content):
        self.content += content

    def endElement(self, name):
        attrs = self.attrstack.pop()
        if not self.feed:
            return
        if name != 'outline':
            self.feed.addChildElement(name, attrs, self.content)
            return

        # create a thread to process the feed
        t = threading.Thread(target=self.processFeed, args=(self.feed,))
        self.threads.append(t)
        t.start()
        self.feed = None

    def createFeed(self, attrs):
        # Normalize attribute names to lower case
        attrs = dict([(k.lower(), v) for k, v in attrs.items()])

        # get common attributes
        name = attrs.get('text') or attrs.get('title')
        if not name:
            return
        nick = attrs['nick'] = attrs.get('nick', name.lower())

        # select by nickname
        if self.nicks and nick not in self.nicks:
            return

        # observe hours (in UTC!) unless only some feeds are requested
        hours = attrs.get('hours')
        if hours and not self.nicks and not _matchHours(hours, time.gmtime()[3]):
            return

        # create a feed instance based on the OPML type attribute
        kind = attrs.get('type', 'rss').lower()
        if kind == 'rss':
            uri = attrs.get('xmlurl')
            if not uri:
                return
            feed = RSSFeed(attrs, name, uri)
        elif kind == 'x-plagg-html':
            uri = attrs.get('htmlurl')
            if not uri:
                return
            feed = HTMLFeed(attrs, name, uri)
        elif kind == 'x-plagg-computed':
            uri, suite = attrs.get('htmlurl'), attrs.get('commands')
            if not suite:
                return
            feed = ComputedFeed(attrs, name, uri, suite)
        else:
            return

        feed.path = os.path.join(self.newspath, nick)

        # disable the cache if only some feeds are requested
        if self.nicks:
            feed.use_cache = False

        return feed

    def processFeed(self, feed):
        if self.fetchFeed(feed):
            e = BlosxomEntries(feed.path)
            e.logging = VERBOSE
            new = e.processFeed(feed)
            if new:
                with self.lock:
                    self.newentries.append((e.name, new))

    def fetchFeed(self, feed):
        try:
            feed.getFeed()
        except httplib.HTTPException as e:
            sys.stderr.write(("Feed: %s (%s): %s\n" % (
                feed.name, feed.uri, e.__class__.__name__
            )).encode(ENCODING, 'replace'))
            return
        except Exception as e:
            import traceback
            if VERBOSE > 1:
                with self.lock:
                    sys.stderr.write("Feed: %s (%s)\n" % (
                        feed.name.encode(ENCODING, 'replace'), feed.uri
                    ))
                    traceback.print_exc()
                self.errors += 1
            else:
                e_str = str(e).lower()
                for msg in (
                    'timed out', 'connection refused', 'reset by peer',
                    'name resolution', 'no route'
                ):
                    if e_str.find(msg) >= 0:
                        break
                else:
                    sys.stderr.write(("Feed: %s (%s)\n%s: %s\n" % (
                        feed.name, feed.uri, e.__class__.__name__, e
                    )).encode(ENCODING, 'replace'))
                    self.errors += 1
            return

        if VERBOSE > 2:
            with self.lock:
                _pprint.pprint(feed.feed)
                if 'bozo_exception' in feed.feed:
                    print feed.feed['bozo_exception']

        return True

    def singleFeed(self, url, name):
        """Handles a single feed URL"""
        feed = self.createFeed({'xmlurl': url, 'text': name})
        if feed:
            self.processFeed(feed)

    def newEntries(self):
        body = ['<ul>']
        for feed, entries in self.newentries:
            body.append(u'  <li>%s</li>\n  <ul>' % feed)
            for e in entries:
                body.append(u'    <li>%s</li>' % e.newSummary())
            body.append('  </ul>')
        body.append('</ul>')
        if len(body) > 2:
            e = Entry()
            e.setEntry('Latest news (%s)' % time.strftime('%H:%M:%S'), u'\n'.join(body))
            e.setMeta(source='plagg')
            e.write(self.newspath, '.txt', overwrite=True, fname='Latest')
