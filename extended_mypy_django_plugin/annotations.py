from __future__ import annotations

from typing import Generic, TypeVar

from django.db import models

T_Parent = TypeVar("T_Parent")
T_Obj = TypeVar("T_Obj")


class Concrete(Generic[T_Parent]):
    """
    The ``Concrete`` annotation exists as a class with functionality for both
    runtime and static type checking time.

    At static type checking time (specifically with ``mypy``) it is used to create
    a type that represents the Union of all the concrete children of some
    abstract model.

    .. automethod:: cast_as_concrete
    """

    @classmethod
    def cast_as_concrete(cls, obj: T_Obj) -> T_Obj:
        """
        This can be used to change the type of an abstract django model to be only
        a concrete decedent.

        At runtime this will raise an exception if the object is an abstract model or class.

        At static type checking time this will change the type of the variable being assigned to::

            from typing import Self, cast
            from extended_mypy_django_plugin import Concrete

            class MyAbstractModel(Model):
                class Meta:
                    abstract = True

                @classmethod
                def new(cls) -> Self:
                    cls = Concrete.cast_as_concrete(cls)
                    reveal_type(cls) # type[Concrete1] | type[Concrete2] | type[Concrete3] | ...
                    ...

                def get_self(self) -> Self:
                    self = Concrete.cast_as_concrete(self)
                    reveal_type(self) # Concrete1 | Concrete2 | Concrete3 | ...
                    ...

        This can also be used outside of a model method::

            model: type[MyAbstractModel] = Concrete1
            narrowed = Concrete.cast_as_concrete(model)
            reveal_type(narrowed) # Concrete1 | Concrete2 | Concrete3 | ...
        """
        if isinstance(obj, type):
            if not issubclass(obj, models.Model) or (
                (Meta := getattr(obj, "Meta", None)) and getattr(Meta, "abstract", False)
            ):
                raise RuntimeError("Expected a concrete subclass")

        elif not isinstance(obj, models.Model) or obj._meta.abstract:
            raise RuntimeError("Expected a concrete instance")

        return obj


class DefaultQuerySet(Generic[T_Parent]):
    """
    This is used to annotate a model such that the mypy plugin may turn this into
    a union of all the default querysets for all the concrete children of the
    specified abstract model class, or of that model when it is a concrete model
    """
