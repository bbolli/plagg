plagg.tar.gz: README plagg *.py news.opml
	tar czf plagg.tar.gz $^

README.inc: README.t
	textile -o1 <$^ >$@

README.html: README.t
	-textile <$^ | tidy -asxml -i -n -wrap 96 >$@

README: README.html
	lynx -dump $^ >$@
