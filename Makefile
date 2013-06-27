ALL: plagg.tar.gz README.inc

.PHONY: dist release install test clean

source := $(shell cat MANIFEST)

plagg.tar.gz: ${source}
	tar -czf $@ $^

README.inc: README.md
	markdown <$^ | perl -pe's!(</?h)(\d)>!$$1.($$2+1).">"!ge' >$@

README.html: README.md
	-markdown <$^ | tidy -utf8 -asxml -i -n -q >$@

README: README.html
	w3m -dump $^ >$@

dist: ${source}
	python setup.py sdist

# provide a Regex-escaped variant of $(V) for grep
VE := $(subst .,\.,$(V))

release:
	grep -q 'Version $(VE)' README.md || \
		{ echo "No version $(V) in README.md"; exit 1; }
	grep __version__ plagglib/Plagg.py | grep -q '$(VE)' || \
		{ echo "No version $(V) in plagglib/Plagg.py"; exit 1; }
	git tag | grep -q '$(VE)' || \
		{ git commit -am"Version $(V)"; git tag v$(V) -m v$(V); }
	make dist

install: plagg.tar.gz
	su -c "python setup.py install"

test: clean
	./plagg -nvvv -d t news.opml ongoing dilbert uf joyoftech >log 2>&1 && \
	./plagg -vvv -d t -fF http://staff.tumblr.com/rss tumblr >>log 2>&1

clean:
	-rm -rf ~/.cache/plagg t log

# vim: set noet:
