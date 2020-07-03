"""Setup for pgq module.
"""

from setuptools import setup

setup(
    name = "pgq",
    description = "PgQ client library for Python",
    version = '3.4.1',
    license = "ISC",
    url = "https://github.com/pgq/python-pgq",
    maintainer = "Marko Kreen",
    maintainer_email = "markokr@gmail.com",
    packages = ['pgq', 'pgq.cascade'],
    install_requires = ['skytools'],
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: ISC License (ISCL)",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Database",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
    ]
)

