# plagg, a RSS aggregator

## 0. What is this?

plagg is a weblog/news aggregator that works in conjunction with
[Rael Dornfest's](http://www.raelity.org) [blosxom](http://www.blosxom.com).
It can be easily extended to support other blogging tools.

plagg reads an OPML file containing a list of RSS or Atom feeds, and
generates blosxom blog entries from these feeds. The items of each feed
are generated into their own directory/blosxom category, which allows to
read the news all at once or per feed.

You can see examples of plagg's output [on my news page](http://drbeat.li/news).


## 1. Installation

1. Download [plagg](http://drbeat.li/py/plagg/plagg.tar.gz)
2. Untar the distribution file to a directory of your choice
3. Run `python setup.py install` as root
4. Set up an [OPML](#opml) file containing the feeds you'd like to read
5. Run `plagg -d` _newsdir_ _opmlfile_ as often as you like from a cron job, where _newsdir_ is somewhere within your blosxom data directory
6. Enjoy your personalized news feed!


## 2. Usage

### 2.1. Synopsis

    plagg -fFnovVh [-t timeout] [-d newsdir] [opmlfile [nickname ...]]

### 2.2. Options

* -f: Don't write the entry footers. Use this option if your blosxom template
      includes a footer.
* -F: Run `plagg` for a single feed whose URL is _opmlfile_. One _nickname_ is
      mandatory and indicates the name of the folder within _newsdir_ where
      the entries get written.
* -n: Write a file _newsdir_/`Latest.txt` that contains the new entries.
* -o: Also generate entries older than one week. These are normally suppressed.
* -v: Be verbose. May be repeated for additional effect.
* -t: Set a global timeout for the whole run.
* -V: Display version information and exit.
* -h: Display usage information and exit.
* -d _newsdir_: The destination directory in subdirectories of which the
      news items are stored. This should be inside your blosxom data directory
      so that blosxom can find and display the items.

### 2.3. Arguments

* _opmlfile_: The OPML file containing the feeds to read and generate news
  items from, or the feed URL if the `-F` option was given.
* _nickname_: If given, updates only the feeds with the given nicknames
  (ignoring their `hours` attribute), otherwise updates all feeds. If `-F`
  was give, the name of the feed.

The default arguments for _opmlfile_ and _destdir_ can be set in the `plagg` script.


## 3. The OPML file

The distribution contains my OPML file as an example.

The basic OMPL syntax is defined in the [OPML specification](http://www.opml.org/spec).

### 3.1. RSS/Atom feeds

Set the `type` attribute to `"rss"`. This is the default feed type.
Plagg reads the feed given by the `xmlUrl` attribute and generates news items
from its content.

Example:

    <outline text="Linux Weekly News" nick="lwn" type="rss"
        htmlUrl="http://lwn.net/" xmlUrl="http://lwn.net/headlines/rss"
    />

The `htmlUrl` attribute is not used by `plagg` itself, but by `opml.xsl`, which
I use to generate my [blogroll](http://drbeat.li/news/news.opml).

### 3.2. HTML scraping

Set the `type` to `"x-plagg-html"`. In this case, plagg reads the HTML page
whose URL is in the `htmlUrl` attribute. There are two ways of specifying how to
scrape: Using a regex or using [XPath][XPATH] expressions.

The result of the scraping is either an image link or an `<iframe>` tag, a title
and optionally a body. The iframe, if any, overrides the image link.

When the match happens against the page's HTML source, all relative URLs have
already been converted to absolute ones, which means that you can't simply copy
a link from a page's HTML source. `<img>` tags end with `" />"`.

#### 3.2.1 Regex

Define the `<regex>` child element of `<outline>` to extract an item title, an
image link or an iframe and, optionally, a body. I use this type to grab a few
comics off sites that don't provide an RSS feed.

There are two ways to specify the regex:

* Using named groups ("`(?P<name>...)`" regex syntax): This requires you to
  define the regex using three named groups called `link` or `iframe`, `title`
  and `body`, which are used as their name indicates (cf. APOD). If you want to
  scrape an item body, you must use this kind of regex.
* Using numbered groups ("`(...)`" regex syntax): The first group defines the
  link, the second one defines the title (cf. Dilbert).

Example:

    <outline text="Dilbert" type="x-plagg-html" htmlUrl="http://www.dilbert.com/">
        <regex>&lt;img src="(http://www\.dilbert\.com/comics/dilbert/archive/images/dilbert(\d+)\.[gj][ip][fg])"</regex>
    </outline>

Here, the whole `src` attribute (i.e. the outer set of parentheses) becomes the
image link, and the number after "dilbert" becomes the entry title.

#### 3.2.2 XPath

Define the child elements `<image-xpath>` or `<iframe-xpath>`, `<title-xpath>`
and optionally `<body-xpath>`.

Each element's content is an XPath expression that is looked up in the HTML body
of the page.

Example:

    <outline text="EOPotD" type="x-plagg-html" htmlUrl="http://earthobservatory.nasa.gov/IOTD/">
        <title-xpath>//div[@class='img-desc']/h3/a</title-xpath>
        <image-xpath>//img[@class='lf']/@src</image-xpath>
        <body-xpath>//div[@class='img-desc']//p</body-xpath>
    </outline>

The XPath expressions are limited to what the Python ElementTree implementation
supports, plus `…/text()` to access an element's text content, and `…/@attr` to
access an element's attribute value.

### 3.3. Computed items

Set `type` to `"x-plagg-computed"`, and set the `commands` attribute to the
Python commands that should be executed. These commands should set `self.itemLink`
and optionally `self.itemTitle` and `self.itemBody` (cf. Garfield)

Example:

    <outline text="Garfield" type="x-plagg-computed" htmlUrl="http://garfield.ucomics.com"
        commands="import time&#10;tm = time.gmtime()&#10;self.itemTitle = '%02d%02d%02d' % (tm[0] % 100, tm[1], tm[2])&#10;self.itemLink = 'http://images.ucomics.com/comics/ga/%d/ga%s.gif' % (tm[0], self.itemTitle)"
        hours="8"
    />

Please keep in mind that in the actual OPML file, the linefeeds have to be
escaped as <code>&amp;#10;</code>.

### 3.4. Saving scraped bits

This feature is available for HTML-scraped and computed items.

Using the `savePath` and `saveUrl` attributes, it is possible to save
whatever the link points to. `savePath` indicates the directory in the local file
system where the file should be saved; `saveUrl` defines the URL that is
substituted instead of the original URL (cf. Userfriendly).

Example: `savepath="/home/myself/www/news/uf" saveurl="/news/uf"`

If necessary, you can define the `referrer` attribute which will be passed in
the HTTP request. The default referrer is either the `link` attribute, or, if
empty, the item link itself.

### 3.5. OPML extensions

`plagg` extends the `<outline>` element with the following attributes and elements:

#### 3.5.1. Time restrictions

This is a new attribute of `<outline>`.

**`hours`="string"**

Defines a set of hours of the day. The feed is read only during these hours.
Values are in 24-hour format relative to [UTC](http://en.wikipedia.org/wiki/Coordinated_Universal_Time).
Ranges may be given as `from-to`; separate simple values or ranges with a comma.
The range includes both `from` and `to` values.

Example: `hours="8-10,15,22"`

#### 3.5.2. Overriding a feed's directory name

This is a new attribute of `<outline>`.

**`nick`="string"**

Sets the "nickname" of a feed. The nickname is used as directory name under
_newsdir_ and when selectively updating with the _nickname_ command line
argument. The default nickname of an outline element is the lowercase
`text` attribute.

#### 3.5.3 Replacements: `<replace>`

This is a new, repeatable child element of `<outline>`.

    <replace what="body" from="regex" to="string"/>

Defines a replacement inside an item's element. Use this to remove ads from an item,
for example (cf. Engadget). The allowed values for `what` are "body", "link" and "title".

Example:

    <replace what="body" from="(?s)&lt;div&gt;&lt;span&gt;.*?&lt;/span&gt;.*?&lt;/div&gt;" to=""/>

This deletes every `<div>` that immediately begins with a `<span>`.

The `to` attribute is optional. If omitted, the text matched by the `from` regex is deleted.

Please keep in mind that in the actual OPML file, the "less than", "greater than"
and "quote" signs in attribute values have to be escaped as `&lt;`, `&gt;` and `&quot;`,
respectively.

#### 3.5.4 Ignoring the entry date

This is a new attribute of `<outline>`.

**`ignoredate`="yes"**

If "yes", the entry's date is ignored and the current time used instead. Useful
for feeds that are published with delays of more than one hour.

#### 3.5.5 Tidying the feed HTML

This is a new attribute of `<outline>`.

**`tidy`="no"**

The default value is "yes". If "yes", the entry body is run through `tidy`, an
external tool that cleans up HTML. Tidy must be installed in `/usr/bin`.

#### 3.5.6 Choosing the entry body

This is a new attribute of `<outline>`.

**`body`="none"**
**`body`="summary"**

The default value is the empty string which will use the full article. If
"empty", the entry's body will be empty. If "summary", and the feed contains
both the full article and a summary, use the summary instead of the full
article.

#### 3.5.7 Adjusting the HTML header level

This is a new attribute of `<outline>`.

**`h-adjust`="n"**

The default value is zero. The HTML elements `h1` to `h4` have their heading
level adjusted by the indicated amount. Useful values are in the range -2..2.

#### 3.5.8 Setting HTTP request headers `<header>`

This is a new, repeatable child element of `<outline>`.

It has a `name` and `value` attribute that specify a HTTP header that should be
sent along with the request.

Example:

    <header name='Cookie' value='sessionID=1c521c788d5da9a1448bd93a63e9b78ba54f902a'/>

#### 3.5.9 Skipping entries: `<skip>`

This is a new child element of `<outline>`.

    <skip title="regex"/>

Skip entries whose titles match the regex given. The matching occurs before
the title text replacements, if any.

Example:

    <skip title="^heise\+"/>

### 3.6. Rendering the OPML file as XHTML

The distribution tar file contains the XSL style sheet `opml.xsl` that transforms
an OPML file into XHTML. Place your OPML file and the style sheet (or symbolic links
to them) in a directory that your HTTP server can access and you can display
a properly indented view of your OPML file just by entering its URL in your browser.
Modern browsers understand enough of XML to apply the XSL file before displaying the page.

If you want to adjust the resulting XHTML, you have to adjust the location and name
of your CSS style sheet in the XSL file, as well as the CSS class names of the generated
`<div>` tags.


## 4. Changelog

* Version 1.0, 2004-10-29:
  - Initial public release
* Version 1.1, 2004-11-11:
  - Added HTTP caching, thanks to Joe Gregorio's [httpcache.py](http://bitworking.org/projects/httpcache)
* Version 1.2, 2004-11-25:
  - Print an exception trace only at log level 2 and above
  - Generate a feed title attribute with the feed's tagline
  - Send the correct User-Agent string which was lost by using httpcache.py
    (patch sent to and [accepted by](https://bitworking.org/news/2004/12/httpcache_py_1_0_2/) Joe Gregorio)
* Version 1.3, 2004-12-29:
  - Added the `-n` option
  - Process feeds only if they have changed
  - Allow more than one nickname on the command line
* Version 1.4, 2006-03-26
  - Allow multiple link and body replacements
  - Improved [Unicode](http://www.unicode.org) support
* Version 1.5, 2007-02-08
  - Moved to UTF-8 encoding
* Version 1.5a, 2007-02-09
  - Bugfix for HTML-scraped feeds
* Version 1.6, 2007-05-23
  - Ignore entries from the future
* Version 1.7, 2007-06-06
  - Added the attribute `ignoredate` which can be set to `yes` for ignoring
    an entry's date and instead use the current time
  - Verbose levels of 3 and higher turn on feedparser's debugging output
* Version 1.7a, 2007-06-06
  - Fixed a stupid untested last-minute change
* Version 1.8, 2008-12-17
  - Implemented a timeout for TCP/IP socket operations
* Version 1.9, 2009-11-25
  - Use feedparser's own ETag/Modified handling for RSS feeds. This gets us
    the correct base URI handling for feeds that contain relative URIs.
    This was broken by using HTTPCache.
* Version 1.10, 2009-12-30
  - Add `replaceTitle` handling
* Version 1.11, 2010-01-07
  - **Backwards-incompatible change:** unify the body, link and title
    replacements into one tag. This requires changes to your OPML file.
  - Handle ETag and Last-Modified HTTP headers of scraped HTML pages myself,
    eliminating the need for `httpcache.py`.
* Version 1.12, 2012-02-06
  - Add the -f option to suppress entry footers
  - Use the tumblr.com entry id as file name if present
* Version 1.12a, 2012-02-06
  - Fix the tumblr id parsing if the entry has no link
* Version 2.0, 2012-02-07
  - Add option -d to define the newsdir instead of the second non-option argument
  - Add option -F to generate posts from a single feed URL
* Version 2.1, 2012-02-09
  - If the entry starts with a link, use it and delete it from the body
  - Make tidying the entry body optional
  - Gracefully handle OSErrors while calling tidy
  - Add the missing "ignoredate" documentation
* Version 2.2, 2012-07-20
  - Process the feeds in parallel
  - Allow computed feeds to generate `<iframe>`s instead of images
* Version 2.3, 2013-01-29
  - Add option -o to generate entries older than one week
  - Remove the entry title if it matches the start of the body
  - Follow the [XDG recommendations][XDG] for the cache location
  - Don't filter new HTML5 elements
* Version 2.4, 2013-06-27
  - Disable the HTTP cache if only some feeds are requested
  - Add support for media:content links
  - Don't use Markdown for Latest.txt
  - Provide a "release" target in the Makefile
* Version 2.5, 2014-03-18
  - Remove the entry title if it appears in the body
  - Add support to force using an entry's summary
* Version 3.0, 2014-03-28
  - **Backwards-incompatible change:** move the scraping regex into its own
    child element of `<outline>`
  - Add support for [XPath][XPATH] scraping

[XDG]: http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html
[XPATH]: http://www.w3.org/TR/xpath/


## 5. TODO

* Should support `skipHours` from the RSS feed instead of using `hours`
* Support RSS enclosures
* Use a proper [XML namespace](http://www.w3.org/TR/REC-xml-names/) for my OPML extensions


## 6. Author

Beat Bolli `<me+plagg@drbeat.li>`, http://drbeat.li/py/plagg

<!-- vim: set tw=80 et: -->
