h1. plagg, a RSS aggregator


h2(#what). 0. What is this?

plagg is a weblog/news aggregator that works in conjunction with
"Rael Dornfest's":http://www.raelity.org "blosxom":http://www.blosxom.com.
It can be easily extended to support other blogging tools.

plagg reads an OPML file containing a list of RSS or Atom feeds, and
generates blosxom blog entries from these feeds. You can see
examples of plagg's output "on my news page":http://www.drbeat.li/news.


h2(#install). 1. Installation

# Download and install "Mark Pilgrim's":http://diveintomark.org "Ultra-liberal Feed Parser 3.3":http://feedparser.org/
# Download "plagg":plagg.tar.gz
# Untar the distribution file to a directory of your choice
# Run @su -c "python setup.py install"@
# Set up an "OPML":#opml file containing the feeds you'd like to read
# Run @plagg@ _opmlfile_ _newsdir_ as often as you like from a cron job


h2(#usage). 2. Usage

h3. 2.1. Synopsis

pre. plagg -nvVh [opmlfile [newsdir [nickname ...]]]

h3. 2.2. Options

dl. -n: Write a file _newsdir_/@Latest.txt@ that contains the new entries.
-v: Be verbose. May be repeated for additional effect.
-V: Display version information and exit.
-h: Display usage information and exit.

h3. 2.3. Arguments

dl. opmlfile: The OPML file containing the feeds to read and generate news items from.
newsdir: The destination directory in subdirectories of which the news items are stored. This should be inside your blosxom data directory so that blosxom can find and display the items.
nickname: If given, updates only the feeds with the given nicknames (ignoring their @hours@ attribute), otherwise updates all feeds.

The default arguments for opmlfile and destdir can be set in the @plagg@ script.


h2(#opml). 3. The OPML file

The distribution contains my OPML file as an example.

The basic OMPL syntax is defined in the "OPML specification":http://www.opml.org/spec.

I have added a few attributes to the @<outline>@ element to allow
for some interesting features:

h3. 3.1. General attributes

These are attributes that work for each kind of feed type.

h4. 3.1.1. Body replacements

*@bodyFrom@="regex", @bodyTo@="string"*

Defines a replacement inside the item's body. Use this to remove ads from an item,
for example (cf. Engadget).

Example:

literal. <pre>bodyFrom="(?s)&lt;div&gt;&lt;span&gt;.*?&lt;/span&gt;.*?&lt;/div&gt;" bodyTo=""</pre>

This deletes every @<div>@ that immediately begins with a @<span>@.

Please keep in mind that in the actual OPML file, the "less than", "greater than"
and "quote" signs have to be escaped as @&amp;lt;@, @&amp;gt;@ and @&amp;quot;@,
respectively.

h4. 3.1.2. Link replacements

*@linkFrom@="regex", @linkTo@="string"*

Allows to replace the link to the news item. I use this to have the link
point to the printable page of an item (cf. the Register).

Example: @linkFrom="/$" linkTo="/print.html"@

This appends "print.html" to the end of the link.

h4. 3.1.3. Time restrictions

*@hours@="string"*

Defines a set of hours of the day. The feed is read only during these hours.
Values are in 24-hour format relative to GMT. Ranges may be given as @from-to@;
separate simple values or ranges with a comma.

Example: @hours="8-10,15,22"@

h4. 3.1.4. Overriding the directory name

*@nick@="string"*

Sets the "nickname" of a feed. The nickname is used as directory name under
_newsdir_ and when selectively updating with the _nickname_ command line
argument. The default nickname of an outline element is the lowercase
@text@ attribute.

h3. 3.2. RSS/Atom feeds

Set the @type@ attribute to @"rss"@. This is the default feed type.
Plagg reads the feed given by the @xmlUrl@ attribute and generates news items
from its content.

Example:

literal.. <pre>&lt;outline text="Linux Weekly News" nick="lwn" type="rss"
    htmlUrl="http://lwn.net/" xmlUrl="http://lwn.net/headlines/rss"/&gt;
</pre>

p. The @htmlUrl@ attribute is not used by @plagg@ itself, but by @opml.xsl@, which
I use to generate my "blogroll":http://www.drbeat.li/news/news.opml.


h3. 3.3. HTML scraping

Set the @type@ to @"x-plagg-html"@. In this case, plagg reads the HTML page
whose URL is in the @link@ attribute. It then uses the @regex@ attribute
to extract an item title, a link and, optionally, a body.
I use this type to grab a few comics off sites that don't provide an RSS feed.

There are two ways to specify the regex:

dl. Using named groups ("@(?P<name>...)@" regex syntax): This requires you to include in the regex three named groups called @link@, @title@ and @body@, which are use as their name indicates (cf. APOD). If you want to scrape an item body, you must use this kind of regex.
Using numbered groups ("@(...)@" regex syntax): The first group defines the link, the second one defines the title (cf. Dilbert).

In each case, at the moment the regex is matched against the item body,
all relative URLs have already been converted to absolute ones, which means
that you can't simply copy a regex from a page's HTML source.

Example:

literal.. <pre>&lt;outline text="Dilbert" type="x-plagg-html" link="http://www.dilbert.com/"
    regex="&lt;img src=&quot;(http://www.dilbert.com/comics/dilbert/archive/images/dilbert(\d+)\.[gj][ip][fg])&quot;"
    hours="8-10"/&gt;
</pre>

h3. 3.4. Computed items

Set @type@ to @"x-plagg-computed"@, and set the @commands@ attribute to the
Python commands that should be executed. These commands should set @self.itemLink@
and optionally @self.itemTitle@ (cf. Garfield)

Example:

literal.. <pre>&lt;outline text="Garfield" type="x-plagg-computed" link="http://garfield.ucomics.com"
    commands="import time&#10;tm = time.gmtime()&#10;self.itemTitle = '%02d%02d%02d' % (tm[0] % 100, tm[1], tm[2])&#10;self.itemLink = 'http://images.ucomics.com/comics/ga/%d/ga%s.gif' % (tm[0], self.itemTitle)"
    hours="8"/>
</pre>

Please keep in mind that in the actual OPML file, the linefeeds have to be
escaped as <code>&amp;#10;</code>.

h3. 3.5. Saving scraped bits

This feature is available for HTML-scraped and computed items.

Using the @savePath@ and @saveUrl@ attributes, it is possible to save
whatever the link points to. @savePath@ indicates the directory in the local file
system where the file should be saved; @saveUrl@ defines the URL that is
substituted instead of the original URL (cf. Userfriendly).

Example: @savepath="/home/myself/www/news/uf" saveurl="/news/uf"@

If necessary, you can define the @referrer@ attribute which will be passed in
the HTTP request. The default referrer is either the @link@ attribute, or, if
empty, the item link itself.

h3. 3.6. Rendering the OPML file as XHTML

The distribution tar file contains the XSL style sheet @opml.xsl@ that transforms
an OPML file into XHTML. Place your OPML file and the style sheet (or symbolic links
to them) in a directory that your HTTP server can access and you can display
a properly indented view of your OPML file just by entering its URL in your browser.
Modern browsers understand enough of XML to apply the XSL file before displaying the page.

If you want to adjust the resulting XHTML, you have to adjust the location and name
of your CSS style sheet in the XSL file, as well as the CSS class names of the generated
@<div>@ tags.


h2(#changelog). 4. Changelog

* Version 1.0, ==2004-10-29==:
** Initial public release
* Version 1.1, ==2004-11-11==:
** Added HTTP caching, thanks to Joe Gregorio's "httpcache.py":http://bitworking.org/projects/httpcache
* Version 1.2, ==2004-11-25==:
** Print an exception trace only at log level 2 and above
** Generate a feed title attribute with the tagline
** Send the correct User-Agent string which was lost by using httpcache.py (patch sent to and "accepted by":http://bitworking.org/news/httpcache_py_1_0_2 Joe Gregorio)
* Version 1.3, ==2004-12-29==:
** Added the @-n@ option
** Process feeds only if they have changed
** Allow more than one nickname on the command line


h2(#todo). 5. TODO

* Should use @skipHours@ from the RSS feed instead of using @hours@
* Support RSS enclosures


h2(#author). 6. Author

Beat Bolli @<me&#43;plagg&#64;drbeat&#46;li>@, http://www.drbeat.li/py/plagg

&nbsp;

pre. $Id$
