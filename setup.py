"""Setup for pgq module.
"""

from setuptools import setup


# load version from pgq/__init__.py
_version = None
with open("pgq/__init__.py") as f:
    for ln in f:
        if ln.startswith("__version__"):
            _version = ln.split()[2].strip("\"'")
assert _version

# load info
with open("README.rst") as f:
    ldesc = f.read().strip()
    sdesc = ldesc.split('\n')[0]

setup(
    name="pgq",
    description=sdesc,
    long_description=ldesc,
    version=_version,
    license="ISC",
    url="https://github.com/pgq/python-pgq",
    maintainer="Marko Kreen",
    maintainer_email="markokr@gmail.com",
    packages=["pgq", "pgq.cascade"],
    package_data={"pgq": ["py.typed"]},
    install_requires=["skytools"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: ISC License (ISCL)",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3",
        "Topic :: Database",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
    ]
)

