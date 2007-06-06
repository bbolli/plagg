ALL: plagg.tar.gz README.inc

.PHONY: dist install test clean

source := $(shell cat MANIFEST)

perlexp := 'm{"(.*) \(.*?([0-9]+?) } && print "$1.$2";'
version := $(shell grep '$Id' plagg | perl -ne ${perlexp})

plagg.tar.gz: ${source}
	tar -czf $@ $^

README.inc: README.t
	textile -o1 <$^ >$@

README.html: README.t
	-textile <$^ | tidy -utf8 -asxml -i -n >$@

README: README.html
	lynx -dump $^ >$@

dist: ${source}
	python setup.py sdist

install: plagg.tar.gz
	su -c "python setup.py install"

test: clean
	./plagg -vvv news.opml t ongoing dilbert uf joyoftech >log 2>&1

clean:
	-rm -rf .cache t log
