ALL: plagg.tar.gz README.inc

.PHONY: dist install

source := MANIFEST $(shell cat MANIFEST)

plagg.tar.gz: ${source}
	tar -czf $@ $^

README.inc: README.t
	textile -o1 <$^ >$@

README.html: README.t
	-textile <$^ | tidy -asxml -i -n -wrap 76 >$@

README: README.html
	lynx -dump $^ >$@

dist: ${source}
	python setup.py sdist

install:
	su -c "python setup.py install"
