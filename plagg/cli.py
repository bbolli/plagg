"""Reads an OPML file, gets all feeds in it and writes Blosxom entries
corresponding to the items in the feeds."""

import argparse
import signal
import sys

from . import __version__, Plagg


parser = argparse.ArgumentParser(prog='plagg', description=__doc__)
parser.add_argument('-d', '--dir', help="the destination directory",
                    default='~/bblog/news')
parser.add_argument('-F', '--feed', action='store_true',
                    help="use OPMLFILE as a single feed URL")
parser.add_argument('-m', '--media', metavar='MEDIADIR',
                    help="download media files into this directory; "
                    "format=<base-dir>:<sub-dir>")
parser.add_argument('-n', '--news', action='store_true',
                    help="write a Latest.txt with new entries")
parser.add_argument('-o', '--old', action='store_true',
                    help="also generate entries older than one week")
parser.add_argument('-v', '--verbose', action='count', default=0,
                    help="increase verbosity (may be repeated)")
parser.add_argument('-f', '--no-footer', action='store_false', dest='footer',
                    help="suppress entry footers", default=True)
parser.add_argument('-t', '--timeout', type=int, default=0,
                    help="global timeout in seconds")
parser.add_argument('-V', '--version', action='store_true',
                    help="display plagg's version")
parser.add_argument('opmlfile', nargs='?', default='',
                    help="the file containing your news feeds, or, "
                    "with -F: the feed URL; default=DIR/news.opml")
parser.add_argument('nicknames', nargs='*', default=[],
                    help="only update these feeds")

args = parser.parse_args()
if args.version:
    print(__version__)
    sys.exit(0)
if args.feed:
    if not args.opmlfile or '://' not in args.opmlfile:
        parser.error("-F must be used with a feed URL")
    if len(args.nicknames) != 1:
        parser.error("-F must be used with exactly one nickname")
if args.old is None:
    args.old = bool(args.nicknames)

if args.timeout and hasattr(signal, 'alarm'):
    signal.signal(signal.SIGALRM, signal.default_int_handler)
    signal.alarm(args.timeout)

plagg = Plagg(args)
try:
    if args.feed:
        plagg.singleFeed()
    else:
        plagg.allFeeds()
except KeyboardInterrupt:
    pass
if args.news:
    plagg.newEntries()

sys.exit(plagg.errors and 1 or 0)
