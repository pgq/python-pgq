
VERSION = $(shell python3 setup.py --version)
RXVERSION = $(shell python3 setup.py --version | sed 's/\./[.]/g')
TAG = v$(VERSION)
NEWS = NEWS.rst

all:

clean:
	rm -rf build *.egg-info */__pycache__ tests/*.pyc
	rm -rf .pybuild MANIFEST

xlint:
	tox -e xlint

xclean: clean
	rm -rf .tox dist

test:
	PGDATABASE=testdb TEST_Q_NAME=testq PGHOST=/tmp PGPORT=5120 tox -e py38

checkver:
	@echo "Checking version"
	@grep -q '^pgq $(RXVERSION)\b' $(NEWS) \
	|| { echo "Version '$(VERSION)' not in $(NEWS)"; exit 1; }
	@echo "Checking git repo"
	@git diff --stat --exit-code || { echo "ERROR: Unclean repo"; exit 1; }

release: checkver
	git tag $(TAG)
	git push github $(TAG):$(TAG)

unrelease:
	git push github :$(TAG)
	git tag -d $(TAG)

shownote:
	awk -v VER="$(VERSION)" -f etc/note.awk $(NEWS) \
	| pandoc -f rst -t gfm --wrap=none

