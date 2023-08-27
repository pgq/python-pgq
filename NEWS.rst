NEWS
====

pgq 3.8
-------

* build: convert to pyproject.toml
* typing: add full typing
* ci: drop unmaintained actions

pgq 3.7.3
---------

Fixes:

* worker: another refactor for wait-behind - use dedicated code path for it,
  following main path makes things too complicated.  Fixes the problem of
  missing node location events.
* nodeinfo: set more fields on dead node

pgq 3.7.2
---------

Fixes:

* status: fix crash on dead node

pgq 3.7.1
---------

Fixes:

* worker: fix merge-leaf watermark

pgq 3.7
-------

Fixes:

* worker: another wait-behind fix - avoid too eager switch.

Cleanups:

* Additional typing improvements.

pgq 3.6.2
---------

Fixes:

* worker: detect if wait-behind is finished

pgq 3.6.1
---------

Fixes:

* status: handle root with random provider

pgq 3.6
-------

Features:

* takeover: handle merge workers on takeover
* takeover: move switch of other subscriber before takeover

pgq 3.5.2
---------

Features:

* status command improvements:
  - Switch --compact for shorter output.
  - Coloring when lagging.
  - Order by node name.

Cleanups:

* Disable "universal" build (py2+3)
* Fix release uploads.

pgq 3.5.1
---------

Cleanups:

* Drop Debian packaging
* style: use compact super()
* ci: use new path/env syntax
* Add py.typed

pgq 3.5
-------

* Enable Github actions
* Drop Py2 support.
* Upgrade tox setup.

