"entries.py -- make blog entries from a feed object"

import os
import re
import subprocess
import sys
import time
from urllib.parse import urlsplit

from . import plagg            # for default encoding and config


def _escape(text):
    """Replaces common HTML character entities."""
    return text.replace('&', '&amp;').replace('<', '&lt;'). \
        replace('>', '&gt;').replace('"', '&quot;').replace('\'', '&apos;')


def _linktag(href, text, **attrs):
    """Returns a HTML link tag."""
    a = ''.join([' %s="%s"' % (k, _escape(v)) for k, v in attrs.items() if v])
    return '<a href="%s"%s>%s</a>' % (href, a, text)


def _unescape(text):
    """Replaces common HTML character entities."""
    return text.replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&')

_markup = re.compile(r'<.*?>', re.DOTALL)
_notword = re.compile(r'\W')
_idfirst = re.compile('^[a-zA-Z]')
_idwrong = re.compile('[^0-9a-zA-Z]+')
_body = re.compile('<body>(.*?)</body>', re.IGNORECASE + re.DOTALL)
_tumblr = re.compile(r'\.tumblr\.com/post/(\d+)$', re.IGNORECASE)
_link = re.compile(r'''(?is)^<a href="([^"]+?)">(.*?)</a>((:\s+)|$)''')
_h14 = re.compile(r'(?i)(</?h)([1-4])>')

if time.localtime()[8]:
    tz = time.altzone
else:
    tz = time.timezone


class Entry:
    """Blog entry class.
    Represents one Blosxom blog entry."""

    TidyWarningDone = False

    def __init__(self):
        self.channel = self.item = None
        self._title = self._link = self.body = self.footer = ''
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
        self.setMeta(source=feed.attrs['nick'])

        # body
        bodytype = feed.attrs.get('body', '')
        if bodytype == 'none':
            body = ''
        else:
            body = (
                bodytype != 'summary' and item.get('content', [{}])[0].get('value') or
                item.get('summary', '')
            ).strip()
            body = feed.replaceText('body', body)
        if body and not body.startswith('<'):
            body = '<p>' + body + '</p>'
        try:
            adj = int(feed.attrs['h-adjust'])
        except (KeyError, ValueError):
            pass
        else:
            body = _h14.sub(
                lambda m: '%s%d>' % (m.group(1), int(m.group(2)) + adj),
                body
            )
        self.body = body

        # title
        title = _unescape(item.get('title', '').replace('\n', ' ')).strip()
        if feed.skipEntry('title', title):
            return False
        title = feed.replaceText('title', title)
        # remove the title if it matches the start of the body (for tumblr quotes)
        if len(title) > 20 and title[0] == title[-1] == '"':
            if title.count('"') == 2:
                title = title[1:-1].rstrip('.')
            if title in self.body:
                title = ''
        elif title.endswith('...') and title[:-3] in self.body:
            title = ''
        self._title = title

        # link
        self._link = item.get('link')

        # if the body starts with a link, use it and delete it from the body
        m = _link.match(self.body)
        if m:
            link = m.group(1)
            self.body = self.body[m.end():]
        else:
            link = self._link
        if self._title and link:
            self.title = _linktag(link, self._title)
        else:
            self.title = self._title

        if feed.attrs.get('tidy', 'yes') == 'yes':
            self.body = self.tidy(self.body)

        # tags
        if 'tags' in item:
            self.setMeta(tags=' '.join(t.term.replace(' ', '+') for t in item.tags))

        # footer
        if plagg.FOOTER:
            footer = '\n<p class="blosxomEntryFoot">' + (
                item.get('date') or item.get('modified', '')
            )
            if self._link and (len(self.body) > 2500 or self._link != link):
                footer += '\n[%s]' % _linktag(self._link, 'Link')
            if 'comments' in item:
                footer += '\n[%s]' % _linktag(item['comments'], 'Comments')
            if 'link' in channel:
                footer += '\n[%s]\n</p>' % _linktag(
                    channel['link'], channel['title'], title=channel.get('tagline')
                )
            self.footer = footer + '\n'

        # modification time
        if feed.attrs.get('ignoredate', 'no') != 'yes':
            self.mdate = item.get('date_parsed') or item.get('modified_parsed') or \
                item.get('updated_parsed')
            if self.mdate:
                # convert date/time 9-tuple in UTC to timestamp
                self.tm = time.mktime(self.mdate[:8] + (-1, )) - tz
                self.mdate = time.localtime(self.tm)    # convert timestamp to local 9-tuple

        if plagg.VERBOSE > 1:
            plagg.pprint(('new item', self.__dict__))

        return True

    def setEntry(self, title, body, footer=''):
        self._title = self.title = title
        self.body = body
        self.footer = footer

    def setMeta(self, **meta):
        self.metas.update(meta)

    def makeFilename(self):
        """Sets a suitable file name for the current entry."""
        m = _tumblr.search(self._link) if self._link else None
        if m:
            self.fname = m.group(1)
        else:
            fn = _markup.sub('', self._title)
            if not fn:  # use first 30 non-markup characters if no title
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
        if self.metas:  # this needs the Blosxom "meta" plugin!
            for m in self.metas.items():
                s.append('meta-%s: %s' % m)
            s.append('')
        s.append(self.body)
        if self.item and self.item.get('media_content'):
            s.append('<p class="blosxomMedia">')
            for c in self.item['media_content']:
                url = c['url']
                name = urlsplit(url).path.split('/')[-1]
                s.append('<a href="%s">%s</a>' % (url, name))
            s.append('</p>')
        s.append(self.footer)
        return '\n'.join(s)

    def timestamp(self, suffix):
        if not self.mdate:
            return ''
        return time.strftime('%H:%M:%S', self.mdate) + suffix

    def logSummary(self):
        return self.timestamp(': ') + \
            (_markup.sub('', self._title) or self.fname)

    def newSummary(self):
        return self.timestamp('\N{EN SPACE}') + \
            _linktag('#' + self._id, self._title)

    def write(self, destdir, ext, overwrite=False, fname=None):
        """Writes the entry out to the filesystem."""
        if fname:
            self.fname = fname
        elif not self.makeFilename():
            return 0

        # ignore entries in the future or older than 7 days
        if self.tm:
            now = time.time()
            if self.tm > now:
                return 0
            if not plagg.OLD_ENTRIES and self.tm + 7 * 86400 < now:
                return 0

        fname = os.path.join(destdir, self.fname + ext)

        # if the file exists, we have handled this entry in an earlier run
        if not overwrite and os.path.isfile(fname):
            return 0

        self.makeId()

        # write out the entry
        with open(fname, 'w') as f:
            f.write(self.render())

        # set modification time if present
        if self.tm:
            os.utime(fname, (self.tm, self.tm))

        return 1

    def tidy(self, body):
        if plagg.VERBOSE > 3:
            print('before tidy:', body)
        tidy = ['/usr/bin/tidy', '-asxhtml', '-utf8', '-f', '/dev/null']
        try:
            t = subprocess.Popen(
                tidy, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
            )
            r = t.communicate(body)[0]
        except OSError:
            if not Entry.TidyWarningDone:
                print("Cannot execute " + ' '.join(tidy), file=sys.stderr)
                Entry.TidyWarningDone = True
        else:
            if 0 <= t.returncode <= 1:    # warnings are ok
                # Keep the part between <body> and </body>
                m = _body.search(r)
                body = (m.group(1) if m else r).strip()
            elif plagg.VERBOSE > 3:
                print("tidy errors; body left as-is" % t.returncode)
        if plagg.VERBOSE > 3:
            print('after tidy:', body)
        return body


class Entries:
    """Abstract Entry class.
    Processes blog entries from a feed object."""

    def processFeed(self, feed):
        """Processes each entry of a feed object.
        Returns the new entries."""
        self.new = []
        if not feed.feed:
            return 0      # skip empty feeds
        self.feed = feed
        self.channel = feed.feed.get('channel', {'title': feed.name})
        self.name = self.channel.get('title', feed.name)
        self.items = feed.feed['items']
        # Process the entries
        for item in self.items:
            if 'link' in item:
                item['link'] = feed.replaceText('link', item['link'])
            self.processItem(item)
        return self.new

    def processItem(self, item):
        """Processes an entry for one RSS item. Subclasses must implement this."""
        raise NotImplementedError('Entries.processItem()')


class BlosxomEntries(Entries):
    """Creates Blosxom entries from a feed."""

    def __init__(self, path):
        self.fdir = path        # directory where entries go
        self.fext = '.txt'      # file extension
        self.logging = 0        # logging of new entries
        self.logged = False
        # Create the directory if needed
        if not os.path.isdir(path):
            os.makedirs(path)

    def processItem(self, item):
        """Builds the text of one Blosxom entry, saves it in self.path and
        sets its mtime to the timestamp, if present."""

        entry = Entry()
        if not entry.setFromItem(self.feed, self.channel, item):
            return
        if not entry.write(self.fdir, self.fext):
            return
        if entry._title:
            self.new.append(entry)

        # logging
        if self.logging:
            name = '' if self.logged else self.name + '\n'
            self.logged = True
            plagg.pprint(name + '  ' + entry.logSummary())
