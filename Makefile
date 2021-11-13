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

# get the version
V := $(shell awk -F\" '/__version__/ { print $$2 }' <plagglib/plagg.py)

# provide a Regex-escaped variant of $(V) for grep
VE := $(subst .,\.,$(V))

release:
	grep -q '^\* Version $(VE)' README.md || \
		{ echo "No version $(V) in README.md"; exit 1; }
	if git tag | grep -q '^v$(VE)$$'; then \
		echo "Version $(V) is already tagged"; exit 1; \
	else \
		git commit -am"Version $(V)" && \
		git tag v$(V) -m v$(V) && \
		make dist; \
		cp dist/plagg-$(V).tar.gz ~/public_html/lib; \
	fi

install: plagg.tar.gz
	su -c "python setup.py install"

test: clean
	-./plagg -nvvv -d t news.opml ongoing ch schneier >log 2>&1 && \
	./plagg -vvv -d t -fF https://staff.tumblr.com/rss tumblr >>log 2>&1
	vi log

clean:
	-rm -rf ~/.cache/plagg t log

# vim: set noet:
