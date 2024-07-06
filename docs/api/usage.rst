Usage
=====

To make use of this plugin in code means using the annotation classes that are
provided.

The following examples assume there is an abstract model ``AbstractModel``
with the concrete models ``Concrete1``, ``Concrete2``, and ``Concrete3``.
Additionally, ``Concrete2`` has a custom queryset class called ``Concrete2QS``.

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


Concrete TypeVar
----------------

To create a type var representing any one of the concrete models of an abstract
model, create a ``TypeVar`` object like normal and bind it to the concrete of
the desired model:

.. code-block:: python

    from extended_mypy_django_plugin import Concrete
    from typing import TypeVar


    T_Concrete = TypeVar("T_Concrete", bound=Concrete[AbstractModel])


    def create_row(cls: type[T_Concrete]) -> T_Concrete:
        return cls.objects.create()

    # --------------
    # Equivalent to
    # --------------

    from typing import TypeVar

    T_Concrete = TypeVar("T_Concrete", bound=Concrete1 | Concrete2 | Concrete3)


    def create_row(cls: type[T_Concrete]) -> T_Concrete:
        return cls.objects.create()

Concrete.cast_as_concrete
-------------------------

To type narrow an object as a concrete descendent of that object, the
``Concrete.cast_as_concrete`` may be used:

.. code-block:: python

    from extended_mypy_django_plugin import Concrete


    def takes_model(model: AbstractModel) -> None:
        narrowed = Concrete.cast_as_concrete(model)
        reveal_type(narrowed) # Concrete1 | Concrete2 | Concrete3

    def takes_model_cls(model_cls: type[AbstractModel]) -> None:
        narrowed = Concrete.cast_as_concrete(model_cls)
        reveal_type(narrowed) # type[Concrete1] | type[Concrete2] | type[Concrete3]

Note that at runtime this will raise an exception if the passed in object is
either not a Django model class/instance or is an abstract one.

Using Concrete annotations on classmethods would look like:

.. code-block:: python

    from extended_mypy_django_plugin import DefaultQuerySet
    from django.db import models
    from typing import Self


    class AbstractModel(models.Model):
        class Meta:
            abstract = True

        @classmethod
        def new(cls) -> Self:
            concrete = Concrete.cast_as_concrete(cls)
            reveal_type(concrete) # type[Concrete1] | type[Concrete2] | type[Concrete3]
            created = cls.objects.create()

            # Note that convincing mypy that created matches self, requires this
            assert isinstance(created, cls)

            # Otherwise the return will make mypy complain that it doesn't match self
            return created

        # # TODO: this isn't currently possible
        # def qs(self) -> DefaultQuerySet[Self]:
        #     concrete = Concrete.cast_as_concrete(self)
        #     reveal_type(concrete) # Concrete1 | Concrete2 | Concrete3
        #     return concrete.__class__.objects.filter(pk=self.pk)

    class Concrete1(AbstractModel):
        pass

    class Concrete2(AbstractModel):
        pass

    class Concrete3(AbstractModel):
        pass

    model: type[AbstractModel] = Concrete1
    instance = model.new()
    reveal_type(instance) # Concrete1 | Concrete2 | Concrete3

    # # TODO: the qs method specific to which instance isn't possible at the moment
    # qs = instance.qs()
    # reveal_type(qs) # QuerySet[Concrete1] | Concrete2QS | QuerySet[Concrete3]

    specific = Concrete1.new()
    reveal_type(specific) # Concrete1

    # # TODO: the qs method specific to which instance isn't possible at the moment
    # specific_qs = instance.qs()
    # reveal_type(specific_qs) # QuerySet[Concrete1]

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
