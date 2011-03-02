ALL: plagg.tar.gz README.inc

.PHONY: dist install test clean

source := $(shell cat MANIFEST)

plagg.tar.gz: ${source}
	tar -czf $@ $^

README.inc: README.t
	textile -o1 <$^ >$@

README.html: README.t
	-textile <$^ | tidy -utf8 -asxml -i -n >$@

README: README.html
	w3m -dump $^ >$@

dist: ${source}
	python setup.py sdist

install: plagg.tar.gz
	su -c "python setup.py install"

test: clean
	./plagg -vvv news.opml t ongoing dilbert uf joyoftech >log 2>&1

clean:
	-rm -rf .cache t log
