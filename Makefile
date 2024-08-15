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
	python3 setup.py sdist

# get the version
V := $(shell awk -F\" '/__version__/ { print $$2 }' <plagg/__init__.py)

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

PLAGG = python3 -m plagg
FEEDS ?= ongoing ch crypto-gram
test: clean
	-$(PLAGG) -nvv -d t news.opml $(FEEDS) >>log 2>&1
	$(PLAGG) -vv -d t -m t/bb_rss:media -f -F https://swiss.social/@bbolli.rss bb_rss >>log 2>&1
	vi log

clean:
	-rm -rf ~/.cache/plagg t log

# vim: set noet:
