Extended ``django-stubs``
=========================

This is an extension on the `django-stubs`_ project that attempts to make it
possible to work with abstract Django ORM models as if they represent all the
concrete models that extend from them.

There are also some extra changes to improve the experience of using this
``mypy`` plugin.

The intention is to get this code working and tested and documented before
getting those changes into the `django-stubs` project itself.

.. _django-stubs: https://github.com/typeddjango/django-stubs

Built Docs
----------

https://extended-mypy-django-plugin.readthedocs.io

History
-------

This project comes from working on a large Django project (millions of lines of
code) that has varying levels of typing maturity within it. There is work to
get this project onto the latest version of ``mypy`` and ``django-stubs``, but
it is difficult due to 100s of errors introduced by a change from ``mypy`` 1.5.0.

Most of these errors are due to using variables that are typed as Abstract Django
ORM models when they should be typed as the concrete models that inherit those
abstract models. Unfortunately this is not straight forward due to a few factors
that mean what concrete models are available can't be explicitly specified.

This project exists so that it can work with either the old version of
``django-stubs`` that is in use or the latest ``django-stubs``. Support for the
old version is purely a transitional crutch.

Status
------

The code works and has reasonable test coverage, but could do with some more and
needs some more work done on the documentation.
