Primer
======

There are three classes introduced by this plugin (in addition to the rest of
the functionality in `django-stubs`_) to make it easier to work with abstract
Django ORM models.

.. _django-stubs: https://github.com/typeddjango/django-stubs

Abstract and Concrete models
----------------------------

It's useful to first explain what is meant by abstract and concrete models!

In Django ORM, database tables are represented by classes that inherit from
``django.db.models.Model``. These classes will exist under specific Django
apps and are registered as part of Django initialisation.

So for example, a Django app will have a ``models.py`` file that may look like:

.. code-block:: python

    from django.db import models


    class MyModel(models.Model):
        one = models.CharField(max_length=1)

In this case the app will have ``myapp.models.MyModel``.

One of the ways that Django lets the developer share code between models is
with Abstract models. This is where the model gets an ``abstract = True`` in
it's ``Meta`` class:

.. code-block:: python

    from django.db import models


    class MyAbstractModel(models.Model):
        one = models.CharField(max_length=1)

        class Meta:
            abstract = True

This declaration will then not become an actual table in the database, but
rather becomes shared functionality for models that inherit from it. So a
concrete class may look like:

.. code-block:: python

   from myapp.models import MyAbstractModel
   from django.db import models


   class MyModel(MyAbstractModel):
       two = models.CharField(max_length=2)

Now we have a ``MyModel`` class that represents a table in the database with
two columns: ``one`` and ``two``, both of which represent strings.

These concrete models may exist in multiple Django apps. So the developer can
make a Django app that defines some common abstract class, and then in separate
Django apps, some concrete models may inherit from this abstract class.

This means to know what concrete models exist for ``MyAbstractModel`` the
``mypy`` plugin must know which Django apps are installed and have inherited
from the Abstract model.

The ``objects`` manager
-----------------------

To create rows in a database table, these model classes will be given a
"manager" to be the bridge between the model class itself and the database. The
default one given to model classes is given as the ``objects`` attribute.

So for example, to create a row in the database for the table that ``MyModel``
represents, the developer would say:

.. code-block:: python

    from myapp.models import MyModel

    my_row = MyModel.objects.create(one="1", two="22")

Note that because ``MyAbstractModel`` doesn't actually represent any specific
table, this class does not get the ``objects`` attribute and rows in the
database cannot be made for these models (as they are by definition,
incomplete).

This means if we have a function that takes in any of the concrete models for
that abstract class, this becomes a type error:

.. code-block:: python

    from myapp.models import MyAbstractModel
    from myapp.code import process_row


    def create_and_process(model_cls: type[MyAbstractModel], **kwargs) -> None:
        # Using **kwargs is bad, but it's irrelevant to what is being demonstrated
        row = model_cls.objects.create(**kwargs)
        process_row(row)

On this code after ``mypy`` 1.5.0 and ``django-stubs`` 4.2.4, there will be a
type error because if ``model_cls`` is the ``MyAbstractModel`` class itself,
then there is no ``objects`` on the class and this code will fail at runtime!

What the developer actually wants to do is:

.. code-block:: python

    from myapp.models import MyConcreteModel1, MyConcreteModel2
    from myapp.code import process_row


    def create_and_process(model_cls: MyConcreteModel1 | MyConcreteModel2, **kwargs) -> None:
        # Using **kwargs is bad, but it's irrelevant to what is being demonstrated
        row = model_cls.objects.create(**kwargs)
        process_row(row)

However this makes for brittle code because:

* It doesn't communicate to readers the intention of ``model_cls`` (any
  concrete model of ``MyAbstractModel``).
* It fails if some of the concrete models are in apps that may or may not be
  installed in the Django ``INSTALLED_APPS`` setting, or may even be
  conditionally available to import at all.

The fundamental part of the solution proposed by this extension to
``django-stubs`` is to instead say:

.. code-block:: python

    from extended_mypy_django_plugin import Concrete
    from myapp.models import MyAbstractModel
    from myapp.code import process_row


    def create_and_process(model_cls: Concrete[MyAbstractModel1], **kwargs) -> None:
        # Using **kwargs is bad, but it's irrelevant to what is being demonstrated
        row = model_cls.objects.create(**kwargs)
        process_row(row)

And let the mypy plugin determine which models will make up that Union type.

Custom managers and querysets
-----------------------------

In Django, a collection of rows from the database is represented using a
``QuerySet``. For example:

.. code-block::

    queryset = MyModel.objects.all()

This will be an object that represents all the rows for the table represented
by ``MyModel``. It will be typed as ``django.db.models.QuerySet[MyModel]``.

Django models may be given a custom queryset using one of two methods:

.. code-block:: python

    from django.db import models

    class MyQuerySet(models.QuerySet["MyModel"]):
        ...


    class MyModel(models.Model):
        objects = MyQuerySet.as_manager()

Or

.. code-block:: python

    from django.db import models

    class MyQuerySet(models.QuerySet["MyModel"]):
        ...


    MyModelManager = models.Manager.from_queryset(MyQuerySet)


    class MyModel(models.Model):
        objects = MyModelManager()

In both these cases, the default queryset for ``MyModel`` would be
``MyQuerySet`` rather than ``django.db.models.QuerySet[MyModel]``. This matters
from a typing perspective because when ``mypy`` knows the specific queryset
that should be used, then it can see any custom methods that were added to that
queryset.

Annotations
-----------

.. autoclass:: extended_mypy_django_plugin.Concrete

.. autoclass:: extended_mypy_django_plugin.DefaultQuerySet
