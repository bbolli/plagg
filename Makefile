plagg.tar.gz: README.html plagg *.py news.opml
	tar czf plagg.tar.gz $^

README.inc: README.t
	textile -o1 <$^ >$@

README.html: README.inc
	-tidy -asxml -i -n -wrap 96 <$^ >$@
