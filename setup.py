#! /usr/bin/env python

from distutils.core import setup

setup(
    name = "pgq",
    license = "ISC",
    version = '4.0',
    maintainer = "Marko Kreen",
    maintainer_email = "markokr@gmail.com",
    py_modules = ['pgq', 'pgq.cascade'],
    install_requires = ['skytools', 'psycopg2']
)

