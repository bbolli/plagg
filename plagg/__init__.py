"""Reads an OPML file, gets all feeds in it and writes Blosxom entries
corresponding to the items in the feeds."""

import http.client
from pathlib import Path
import pprint as _pprint
import sys
import threading
import time
import xml.sax

__version__ = "3.2"


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

    VERBOSE = 0
    MEDIA = (None, None)
    FOOTER = True
    TM_CUTOFF = 0

    def __init__(self, args):
        self.logging = self.errors = 0
        self.newentries = []
        self.feed = None
        self.attrstack = []
        self.threads = []
        self.lock = threading.Lock()
        xml.sax.handler.ContentHandler.__init__(self)

        self.opmlfile = args.opmlfile
        self.nicks = args.nicknames
        self.newspath = Path(args.dir).expanduser()
        Plagg.VERBOSE = args.verbose
        if args.media:
            media = args.media.split(':') + ['']
            Plagg.MEDIA = (Path(media[0]).expanduser() / media[1], '/' + media[1])
        Plagg.FOOTER = args.footer
        Plagg.TM_CUTOFF = 0 if args.old else time.time() - 7 * 86400

    def pprint(self, obj):
        with self.lock:
            if isinstance(obj, str):
                print(obj)
            else:
                _pprint.pprint(obj)

    def allFeeds(self):
        opmlfile = self.opmlfile or str(self.newspath / 'news.opml')
        xml.sax.parse(opmlfile, self)
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
        attrs = {k.lower(): v for k, v in attrs.items()}

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

        feed.path = self.newspath / nick

        # disable the cache if only some feeds are requested
        if self.nicks:
            feed.use_cache = False

        return feed

    def processFeed(self, feed):
        if self.fetchFeed(feed):
            e = BlosxomEntries(feed.path)
            e.logging = Plagg.VERBOSE
            new = e.processFeed(feed)
            if new:
                with self.lock:
                    self.newentries.append((e.name, new))

    def fetchFeed(self, feed):
        try:
            feed.getFeed()
        except http.client.HTTPException as e:
            print(f"Feed: {feed.name} ({feed.uri}): {e.__class__.__name__}",
                  file=sys.stderr)
            return
        except Exception as e:
            if Plagg.VERBOSE > 1:
                import traceback
                with self.lock:
                    print(f"Feed: {feed.name} ({feed.uri})", file=sys.stderr)
                    traceback.print_exc()
                self.errors += 1
            else:
                e_str = str(e).lower()
                if not any(e_str.find(msg) >= 0 for msg in (
                    'timed out', 'connection refused', 'reset by peer',
                    'name resolution', 'no route'
                )):
                    print(f"Feed: {feed.name} ({feed.uri}):\n"
                          f"{e.__class__.__name__}: {e}", file=sys.stderr)
                    self.errors += 1
            return

        if Plagg.VERBOSE > 2:
            with self.lock:
                _pprint.pprint(feed.feed)
                if 'bozo_exception' in feed.feed:
                    print(feed.feed['bozo_exception'])

        return True

    def singleFeed(self):
        """Handles a single feed URL"""
        feed = self.createFeed({'xmlurl': self.opmlfile, 'text': self.nicks[0]})
        if feed:
            self.processFeed(feed)

    def newEntries(self):
        body = ['<ul>']
        for feed, entries in self.newentries:
            body.append(f'  <li>{feed}</li>\n  <ul>')
            for e in entries:
                body.append(f'    <li>{e.newSummary()}</li>')
            body.append('  </ul>')
        body.append('</ul>')
        if len(body) > 2:
            e = Entry()
            e.setEntry(f"Latest news ({time.strftime('%H:%M:%S')})", '\n'.join(body))
            e.setMeta(source='plagg')
            e.write(self.newspath, '.txt', overwrite=True, fname='Latest')


from .feed import RSSFeed, HTMLFeed, ComputedFeed  # noqa; circular import
from .entries import BlosxomEntries, Entry  # noqa; circular import
