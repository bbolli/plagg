"Entries.py -- make blog entries from a feed object"

# $Id$

import os, re, time
import Plagg		# for default encoding


def _linktag(href, text):
    """Returns a HTML link tag."""
    return u'<a href="%s">%s</a>' % (href, _decode(text))

def _unescape(text):
    """Replaces the three common HTML character entities."""
    return text.replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&')

_markup = re.compile(r'<.*?>', re.M + re.S)
_notword = re.compile(r'\W')

def _filename(title, desc):
    """Returns a suitable file name for an entry."""
    fn = _markup.sub('', title)
    if not fn:	# use first 30 non-markup characters if no title
	fn = _markup.sub('', desc)[:30]
    fn = fn.replace('&apos;', "'").replace('&quot;', '"')
    fn = _notword.sub('_', fn)
    return fn[:15] + '...' + fn[-5:]

def _encode(text):
    """Converts a unicode string to its iso-8859-15 equivalent."""
    if isinstance(text, unicode):
	return text.encode(Plagg.ENCODING, 'xmlcharrefreplace')
    return text

def _decode(text):
    """Converts a string to its unicode equivalent."""
    if isinstance(text, str):
	text = unicode(text, Plagg.ENCODING, 'replace')
    return text


class Entries:
    """Abstract Entry class.
    Processes blog entries from a feed object."""

    def processFeed(self, feed):
	"""Processes each entry of a feed object."""
	if not feed.feed: return	# skip empty feeds
	self.feed = feed
	channel = feed.feed['channel']
	items = feed.feed['items']
	# Process the entries
	for item in items:
	    if item.has_key('link'):
		item['link'] = feed.replaceLink(item['link'])
	    self.processItem(channel, item)

    def processItem(self, channel, item):
	"""Processes an entry for one RSS item. Subclasses must implement this."""
	raise NotImplementedError('Entries.processItem()')


class BlosxomEntries(Entries):
    """Creates Blosxom entries from a feed."""

    def __init__(self, path):
	self.fdir = path	# directory where entries go
	self.fext = '.txt'	# file extension
	self.logging = 0	# logging of new entries
	self.lastChannel = None
	# Create the directory if needed
	if not os.path.isdir(path):
	    os.makedirs(path)

    def makeEntry(self, channel, item):
	"""Returns the title, body and footer of one Blosxom entry."""

	# The item's title and link are both optional. The following logic
	# determines what goes where:
	# - if there's a title and a link, the title becomes the link.
	# - if there's no title but a link, the link goes into the footer.
	# The footer consists of the date, the item link (if present and no
	# title), and the channel link.
	title = _unescape(item.get('title', '').replace('\n', ' '))
	link = item.get('link')
	if title and link:
	    title = _linktag(link, title)
	body = item.get('content', [{}])[0].get('value') or item.get('description', '')
	body = body.strip()
	if body and not body.startswith('<'):
	    body = '<p>' + body + '</p>'
	footer = '<p class="blosxomEntryFoot">' + item.get('date', '')
	if link and not title:
	    footer += '\n[%s]' % _linktag(link, 'Link')
	footer += '\n[%s]\n</p>\n' % _linktag(channel['link'], channel['title'])

	return title, body, footer

    def processItem(self, channel, item):
	"""Builds the text of one Blosxom entry, saves it in self.path and 
	sets its mtime to the timestamp, if present."""

	title, body, footer = self.makeEntry(channel, item)
	entry = u'\n'.join(map(_decode, [title, body, footer]))

	# determine this entry's filename
	fn = _filename(title, body)
	if not fn: return
	fname = os.path.join(self.fdir, fn + self.fext)

	# if the file exists, we have handled this entry in an earlier run
	if os.path.isfile(fname):
	    return

	# write out the entry
	f = file(fname, 'w')
	f.write(_encode(entry))
	f.close()

	# set modification time if present
	mdate = item.get('date_parsed')
	if mdate:
	    mdate = time.mktime(mdate)	# convert date/time 9-tuple to timestamp
	    os.utime(fname, (mdate, mdate))

	# logging
	if self.logging:
	    currentChannel = channel['title']
	    if self.lastChannel != currentChannel:
		print currentChannel
		self.lastChannel = currentChannel
	    print '  ' + _encode(_markup.sub('', title) or fn)


def _test():
    import Feed
    tests = [
	(Feed.RSSFeed, 'slashdot', 'http://slashdot.org/slashdot.rss'),
	(Feed.RSSFeed, 'bblog', 'http://www.drbeat.li/bblog/hardware/index.rss'),
	(Feed.HTMLFeed, 'dilbert', 'http://www.dilbert.com/', r'<img src="(http://www.dilbert.com/comics/dilbert/archive/images/dilbert(\d+)\..{3,4})"'),
	(Feed.HTMLFeed, 'apod', 'http://antwrp.gsfc.nasa.gov/apod/', r'<img SRC="(http://.*/image/(\d{4}/.*?\..*?))"'),
	(Feed.HTMLSubstituteFeed, 'uf', 'http://www.userfriendly.org/static/', r'<img alt="latest strip" .* src="(http://www.userfriendly.org/cartoons/archives/\d{2}\w{3}/xuf(\d{6})\.gif)">', "/xuf", "/uf"),
    ]
    for t in tests:
	klass, nick, args = t[0], t[1], t[2:]
	feed = klass(nick, *args).getFeed()
	e = BlosxomEntries('test/' + nick)
	e.processEntries(feed)
