ALL: plagg.tar.gz README.inc

.PHONY: dist install

plagg.tar.gz: README README.html MANIFEST setup.py plagg Plagg/*.py news.opml opml.xsl
	tar czf plagg.tar.gz $^

README.inc: README.t
	textile -o1 <$^ >$@

README.html: README.t
	-textile <$^ | tidy -asxml -i -n -wrap 76 >$@

README: README.html
	lynx -dump $^ >$@

dist:
	python setup.py sdist

install:
	su -c "python setup.py install"
