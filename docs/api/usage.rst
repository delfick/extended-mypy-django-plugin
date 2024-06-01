Usage
=====

To make use of this plugin in code means using the annotation classes that are
provided.

The following examples assume there is an abstract model ``AbstractModel``
with the concrete models ``Concrete1``, ``Concrete2`` and ``Concrete3`` and
``Concrete2`` has a custom queryset class called ``Concrete2QS``.

Concrete
--------

To create a union of the concrete models, use the ``Concrete`` annotation:

.. code-block:: python

    from extended_mypy_django_plugin import Concrete


    instance: Concrete[AbstractModel]
    
    # --------------
    # Equivalent to
    # --------------

    instance: Concrete1 | Concrete2 | Concrete3

This also works for types:

.. code-block:: python

    from extended_mypy_django_plugin import Concrete


    cls: Concrete[type[AbstractModel]]

    # --------------
    # Equivalent to
    # --------------

    cls: type[Concrete1 | Concrete2 | Concrete3]


Concrete.type_var
-----------------

To create a type var representing any one of the concrete models of an abstract
model, create a ``TypeVar`` object using ``Concrete.type_var``:

.. code-block:: python

    from extended_mypy_django_plugin import Concrete


    T_Concrete = Concrete.type_var("T_Concrete", AbstractModel)


    def create_row(cls: type[T_Concrete]) -> T_Concrete:
        return cls.objects.create()

    # --------------
    # Equivalent to
    # --------------

    from typing import TypeVar

    T_Concrete = TypeVar("T_Concrete", Concrete1, Concrete2, Concrete3)


    def create_row(cls: type[T_Concrete]) -> T_Concrete:
        return cls.objects.create()

Concrete.cast_as_concrete
-------------------------

To type narrow an object as a concrete descendent of that object, the ``Concrete.cast_as_concrete``
may be used:

.. code-block:: python

    from extended_mypy_django_plugin import Concrete


    def takes_model(model: AbstractModel) -> None:
        narrowed = Concrete.cast_as_concrete(model)
        reveal_type(narrowed) # Concrete1 | Concrete2 | Concrete3

    def takes_model_cls(model: type[AbstractModel]) -> None:
        narrowed = Concrete.cast_as_concrete(model)
        reveal_type(narrowed) # type[Concrete1] | type[Concrete2] | type[Concrete3]

Note that at runtime this will raise an exception if the passed in object is either not a django
model class/instance or is an abstract one.

This may also be used on methods of an Django Model in conjunction with ``typing.Self`` or
``typing_extensions.Self``:

.. code-block:: python

    from extended_mypy_django_plugin import Concrete, DefaultQuerySet
    from django.db import models
    from typing import Self


    class AbstractModel(models.Model):
        class Meta:
            abstract = True

        @classmethod
        def new(cls) -> Concrete[Self]:
            cls = Concrete.cast_as_concrete(cls)
            reveal_type(cls) # type[Concrete1] | type[Concrete2] | type[Concrete3]
            return cls.objects.create()

        def qs(self) -> DefaultQuerySet[Self]:
            self = Concrete.cast_as_concrete(self)
            reveal_type(self) # Concrete1 | Concrete2 | Concrete3
            return self.__class__.objects.filter(pk=self.pk)

    class Concrete1(AbstractModel):
        pass

    class Concrete2(AbstractModel):
        pass

    class Concrete3(AbstractModel):
        pass

    model: type[AbstractModel] = Concrete1
    instance = model.new()
    reveal_type(instance) # Concrete1 | Concrete2 | Concrete3

    qs = instance.qs()
    reveal_type(qs) # QuerySet[Concrete1] | QuerySet[Concrete2] | QuerySet[Concrete3]

    specific = Concrete1.new()
    reveal_type(specific) # Concrete1

    specific_qs = instance.qs()
    reveal_type(specific_qs) # QuerySet[Concrete1]

This is essentially turns into a cast at static time with an extra type narrowing done inside model methods
when passing in the first argument of the function (something that is not possible without the mypy plugin).

DefaultQuerySet
---------------

To create a union of the default querysets for the concrete models of an
abstract class, use the ``DefaultQuerySet`` annotation:

.. code-block:: python

    from extended_mypy_django_plugin import DefaultQuerySet
    from django.db import models


    qs: DefaultQuerySet[AbstractModel]

    # --------------
    # Equivalent to
    # --------------

    qs: models.QuerySet[Concrete1] | Concrete2QuerySet | models.QuerySet[Concrete3]

This also works on the concrete models themselves:

.. code-block:: python

    from extended_mypy_django_plugin import DefaultQuerySet


    qs1: DefaultQuerySet[Concrete1]
    qs2: DefaultQuerySet[Concrete2]

    # --------------
    # Equivalent to
    # --------------

    from django.db import models

    qs1: models.QuerySet[Concrete1]
    qs2: Concrete2QuerySet

It also works on the ``TypeVar`` objects returned by ``Concrete.type_var``:

.. code-block:: python

    from extended_mypy_django_plugin import Concrete, DefaultQuerySet


    T_Concrete = Concrete.type_var("T_Concrete", AbstractModel)


    def get_qs(cls: type[T_Concrete]) -> DefaultQuerySet[T_Concrete]:
        return cls.objects.all()

    # --------------
    # Essentially equivalent to
    # --------------

    from typing import TypeVar, overload

    T_Concrete = TypeVar("T_Concrete", Concrete1, Concrete2, Concrete3)


    @overload
    def create_row(cls: Concrete1) -> models.QuerySet[Concrete1]: ...


    @overload
    def create_row(cls: Concrete2) -> Concrete2QuerySet: ...


    @overload
    def create_row(cls: Concrete3) -> models.QuerySet[Concrete3]: ...


    def create_row(
        cls: type[Concrete1 | Concrete2 | Concrete3],
    ) -> models.QuerySet[Concrete1] | Concrete2QuerySet | models.QuerySet[Concrete3]:
        return cls.objects.create()
