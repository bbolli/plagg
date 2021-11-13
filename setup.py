#!/usr/bin/env python3

from distutils.core import setup
import sys, re, os, subprocess

# patch distutils if it can't cope with the "classifiers" or
# "download_url" keywords
if sys.hexversion < 0x02020300:
    from distutils.dist import DistributionMetadata
    DistributionMetadata.classifiers = None
    DistributionMetadata.download_url = None

import plagglib.plagg
version = plagglib.plagg.__version__

# try to get the development version if we're in a Git repo
if os.path.isdir('.git'):
    try:
        version = subprocess.check_output(
	    ['git', 'describe', '--tags'], text=True
	).strip().lstrip('v')
    except subprocess.CalledProcessError:
        pass

setup(
    name="plagg",
    version=version,
    description="plagg is an RSS/Atom feed aggregator",
    author="Beat Bolli",
    author_email="me+plagg@drbeat.li",
    license="GPL2, see file 'COPYING'",
    url="http://drbeat.li/py/plagg/",
    download_url="http://drbeat.li/py/plagg/plagg.tar.gz",
    packages=['plagglib'],
    scripts=['plagg'],
    classifiers = [
	'Development Status :: 5 - Production/Stable',
	'Environment :: Console',
	'Intended Audience :: End Users/Desktop',
	'License :: OSI Approved :: GNU General Public License (GPL)',
	'Operating System :: POSIX',
	'Programming Language :: Python',
	'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: News/Diary',
        'Topic :: Utilities',
    ]
)
