Extended ``django-stubs``
=========================

This is an extension on the `django-stubs`_ project that makes it possible to
represent all concrete descendants of an abstract Django ORM Model in terms of
those abstract models.

The intention is to get this code working and tested and documented before
getting those changes into the ``django-stubs`` project itself.

.. _django-stubs: https://github.com/typeddjango/django-stubs

Built Docs
----------

https://extended-mypy-django-plugin.readthedocs.io

History
-------

This project comes from working on a large Django project (millions of lines of
code) that has varying levels of typing maturity within it. There is work to
get this project onto the latest version of ``mypy`` and ``django-stubs``, but
the upgrade to ``mypy`` 1.5.0 was made difficult due to 100s of errors that appeared
due to ``mypy`` correctly complaining about abstract model types not having on them
properties that are only on their concrete descendants.
