plagg.tar.gz: README.html plagg *.py news.opml
	tar czf plagg.tar.gz $^

README.html: README
	-textile <$^ | tidy -asxml >$@
