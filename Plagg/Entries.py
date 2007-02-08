"Entries.py -- make blog entries from a feed object"

# $Id$

import os, re, time
import Plagg		# for default encoding


def _escape(text):
    """Replaces the three common HTML character entities."""
    return text.replace('&', '&amp;').replace('<', '&lt;'). \
	replace('>', '&gt;').replace('"', '&quot;').replace('\'', '&apos;')

def _linktag(href, text, **attrs):
    """Returns a HTML link tag."""
    a = ''.join([' %s="%s"' % (k, _escape(v)) for k, v in attrs.items() if v])
    return u'<a href="%s"%s>%s</a>' % (href, a, Plagg.decode(text))

def _unescape(text):
    """Replaces the three common HTML character entities."""
    return text.replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&')

_markup = re.compile(r'<.*?>', re.M + re.S)
_notword = re.compile(r'\W')
_idfirst = re.compile('^[a-zA-Z]')
_idwrong = re.compile('[^0-9a-zA-Z]+')

if time.localtime()[8]:
    tz = time.altzone
else:
    tz = time.timezone


class Entry:
    """Blog entry class.
    Represents one Blosxom blog entry."""

    def __init__(self):
	self.channel = self.item = None
	self._title = self._link = self._body = self.body = self.footer = ''
	self.mdate = self.tm = None
	self.metas = {}

    def setFromItem(self, feed, channel, item):
	"""Initializes self from a feed channel and item.
	The item's title and link are both optional. The following logic
	determines what goes where:
	- if there's a title and a link, the title becomes the link.
	- if there's no title but a link, the link goes into the footer.
	The footer consists of the date, the item link (if present and no
	title), an optional comments link, and the channel link."""
	self.channel = channel
	self.item = item

	# title and link
	self._title = _unescape(item.get('title', '').replace('\n', ' ')).strip()
	self._link = item.get('link')
	if self._title and self._link:
	    self.title = _linktag(self._link, self._title)
	else:
	    self.title = self._title

	# body
	self._body = (
	    item.get('content', [{}])[0].get('value') or
	    item.get('description') or
	    item.get('summary', '')
	).strip()
	body = feed.replaceBody(self._body)
	if body and not body.startswith('<'):
	    body = '<p>' + body + '</p>'
        if Plagg.VERBOSE > 2:
            print 'before tidy:', Plagg.encode(body)
	self.body = self.tidy(body)
        if Plagg.VERBOSE > 2:
            print 'after tidy:', Plagg.encode(self.body)

	# footer
	footer = '\n<p class="blosxomEntryFoot">' + (item.get('date') or item.get('modified', ''))
	if self._link and not self._title:
	    footer += '\n[%s]' % _linktag(self._link, 'Link')
	if item.has_key('comments'):
	    footer += '\n[%s]' % _linktag(item['comments'], 'Comments')
	footer += '\n[%s]\n</p>\n' % _linktag(
	    channel['link'], channel['title'], title=channel.get('tagline')
	)
	self.footer = footer

	# modification time
	self.mdate = item.get('date_parsed') or item.get('modified_parsed')
	if self.mdate:
	    self.tm = time.mktime(self.mdate[:8] + (-1, )) - tz	# convert date/time 9-tuple in UTC to timestamp
	    self.mdate = time.localtime(self.tm)	# convert timestamp to local 9-tuple

        if Plagg.VERBOSE > 1:
            import pprint
            print 'item:',
            pprint.pprint(self.__dict__)

    def setEntry(self, title, body, footer=''):
	self._title = self.title = title
	self._body = self.body = body
	self.footer = footer

    def setMeta(self, **meta):
	self.metas.update(meta)

    def makeFilename(self):
	"""Sets a suitable file name for the current entry."""
	fn = _markup.sub('', self._title)
	if not fn:	# use first 30 non-markup characters if no title
	    fn = _markup.sub('', self.body)[:30]
	fn = fn.replace('&apos;', "'").replace('&quot;', '"')
	fn = _notword.sub('_', fn)
	self.fname = fn[:15] + '...' + fn[-5:]
	return self.fname

    def makeId(self):
	self._id = _idwrong.sub('_', self.fname)
	if not _idfirst.match(self._id):
	    self._id = '_' + self._id
	self.setMeta(entryId=self._id)

    def render(self):
	"""Renders itself, including any metas, if any."""
	s = [self.title]
	if self.metas:	# this needs the Blosxom "meta" plugin!
	    for m in self.metas.items():
		s.append('meta-%s: %s' % m)
	    s.append('')
	s.append(self.body)
	s.append(self.footer)
	return Plagg.encode(u'\n'.join(map(Plagg.decode, s)))

    def timestamp(self, suffix):
	if not self.mdate:
	    return ''
	return time.strftime('%H:%M:%S', self.mdate) + suffix

    def logKey(self):
	return self.channel['title']

    def logSummary(self):
	return self.timestamp(': ') + \
	    Plagg.encode(_markup.sub('', self._title) or self.fname)

    def newKey(self):
	return self.logKey()

    def newSummary(self):
	return self.timestamp(': ') + \
	    _linktag('#' + self._id, self._title)

    def write(self, destdir, ext, overwrite=False, fname=None):
	"""Writes the entry out to the filesystem."""
	if fname:
	    self.fname = fname
	elif not self.makeFilename():
	    return 0

	# ignore entries older than 7 days
	if self.tm and self.tm + 7 * 86400 < time.time():
	    return 0

	fname = os.path.join(destdir, self.fname + ext)

	# if the file exists, we have handled this entry in an earlier run
	if not overwrite and os.path.isfile(fname):
	    return 0

	self.makeId()

	# write out the entry
	f = open(fname, 'w')
	f.write(self.render())
	f.close()

	# set modification time if present
	if self.tm:
	    os.utime(fname, (self.tm, self.tm))

	return 1

    def tidy(self, body):
	ch_in, ch_out = os.popen2([
	    '/usr/bin/tidy', '-asxhtml', '-utf8', '-f', '/dev/null', '-wrap', '78'
	])
	ch_in.write(Plagg.encode(body))
	ch_in.close()
	r = ch_out.readlines()
	ch_out.close()
	# Keep the lines between <body> and </body>
	l, l0, l1 = len(r), 0, len(r) - 1
	while l0 < l and r[l0].strip() != '<body>':
	    l0 += 1
	while l1 > l0 and r[l1].strip() != '</body>':
	    l1 -= 1
	return Plagg.decode(''.join(r[l0+1:l1]))


class Entries:
    """Abstract Entry class.
    Processes blog entries from a feed object."""

    def processFeed(self, feed):
	"""Processes each entry of a feed object.
	Returns the number of new entries."""
	if not feed.feed: return 0	# skip empty feeds
	self.feed = feed
	self.channel = feed.feed['channel']
	self.items = feed.feed['items']
	entries = 0
	# Process the entries
	for item in self.items:
	    if item.has_key('link'):
		item['link'] = feed.replaceLink(item['link'])
	    if self.processItem(item):
		entries += 1
	return entries

    def processItem(self, item):
	"""Processes an entry for one RSS item. Subclasses must implement this."""
	raise NotImplementedError('Entries.processItem()')


class BlosxomEntries(Entries):
    """Creates Blosxom entries from a feed."""

    def __init__(self, app, path):
	self.app = app
	self.fdir = path	# directory where entries go
	self.fext = '.txt'	# file extension
	self.logging = 0	# logging of new entries
	self.oldKey = None
	# Create the directory if needed
	if not os.path.isdir(path):
	    os.makedirs(path)

    def processItem(self, item):
	"""Builds the text of one Blosxom entry, saves it in self.path and 
	sets its mtime to the timestamp, if present."""

	entry = Entry()
	entry.setFromItem(self.feed, self.channel, item)
	if not entry.write(self.fdir, self.fext):
	    return

	# tell Plagg about the new entry
	self.app.newEntry(entry)

	# logging
	if self.logging:
	    newKey = entry.logKey()
	    if self.oldKey != newKey:
		print Plagg.encode(newKey)
		self.oldKey = newKey
	    print '  ' + entry.logSummary()

	return 1
