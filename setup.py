#!/usr/bin/env python

# $Id$

from distutils.core import setup
import sys, re

# patch distutils if it can't cope with the "classifiers" or
# "download_url" keywords
if sys.hexversion < 0x02020300:
    from distutils.dist import DistributionMetadata
    DistributionMetadata.classifiers = None
    DistributionMetadata.download_url = None

from Plagg import Plagg

setup(
    name="plagg",
    version=Plagg.__tarversion__,
    description="plagg is an RSS/Atom feed aggregator",
    author="Beat Bolli",
    author_email="me+plagg@drbeat.li",
    license="GPL2, see file 'COPYING'",
    url="http://www.drbeat.li/py/plagg/",
    download_url="http://www.drbeat.li/py/plagg/plagg.tar.gz",
    packages=['Plagg'],
    scripts=['plagg'],
    classifiers = [
	'Development Status :: 5 - Production/Stable',
	'Environment :: Console',
	'Intended Audience :: End Users/Desktop',
	'License :: OSI Approved :: GNU General Public License (GPL)',
	'Operating System :: POSIX',
	'Programming Language :: Python',
	'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: News/Diary',
    ]
)
