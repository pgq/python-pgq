
all:

clean:
	rm -rf build *.egg-info */__pycache__ tests/*.pyc
	rm -rf debian/python-* debian/files debian/*.log
	rm -rf debian/*.substvars debian/*.debhelper debian/*-stamp
	rm -rf .pybuild MANIFEST

deb:
	debuild -us -uc -b

xclean: clean
	rm -rf .tox dist

sdist:
	rm -f dist/*
	python3 setup.py sdist

upload:
	twine upload dist/*.gz

test:
	TEST_DB_NAME=testdb TEST_Q_NAME=testq PGHOST=/tmp PGPORT=5120 tox -e py38

