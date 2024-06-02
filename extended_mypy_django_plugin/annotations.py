from __future__ import annotations

from collections.abc import Sequence
from typing import Generic, TypeVar, overload

from django.db import models

T_Parent = TypeVar("T_Parent")


class Concrete(Generic[T_Parent]):
    """
    The ``Concrete`` annotation exists as a class with functionality for both
    runtime and static type checking time.

    At runtime it can be used to create special ``TypeVar`` objects that may
    represent any one of the concrete children of some abstract class and
    it can be used to find those concrete children.

    At static type checking time (specifically with ``mypy``) it is used to create
    a type that represents the Union of all the concrete children of some
    abstract model.

    .. automethod:: find_children
    .. automethod:: type_var
    .. automethod:: cast_as_concrete
    """

    @classmethod
    @overload
    def cast_as_concrete(cls, obj: type[T_Parent]) -> type[Concrete[T_Parent]]: ...

    @classmethod
    @overload
    def cast_as_concrete(cls, obj: T_Parent) -> Concrete[T_Parent]: ...

    @classmethod
    def cast_as_concrete(
        cls, obj: type[T_Parent] | T_Parent
    ) -> type[Concrete[T_Parent]] | Concrete[T_Parent]:
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
                def new(cls) -> Concrete[Self]:
                    cls = Concrete.cast_as_concrete(cls)
                    ...

                def get_self(self) -> Concrete[Self]:
                    self = Concrete.cast_as_concrete(self)
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

    @classmethod
    def find_children(cls, parent: type[models.Model]) -> Sequence[type[models.Model]]:
        """
        At runtime this will find all the concrete children of some model.

        That is all models that inherit from this model and aren't abstract
        themselves.
        """
        found: list[type[models.Model]] = []

        from django.contrib.contenttypes.models import ContentType

        content_types = ContentType.objects.filter(app_label=parent._meta.app_label)
        for ct in content_types:
            model = ct.model_class()
            if model is None:
                continue
            if not issubclass(model, parent):
                continue
            if hasattr(model, "Meta") and getattr(model.Meta, "is_abstract", False):
                continue
            found.append(model)

        return found

    @classmethod
    def type_var(cls, name: str, parent: type[models.Model] | str) -> TypeVar:
        """
        This returns an empty ``TypeVar`` at runtime, but the ``mypy`` plugin will
        recognise that this ``TypeVar`` represents a choice of all the concrete
        children of the specified model.
        """
        return TypeVar(name)


class DefaultQuerySet(Generic[T_Parent]):
    """
    This is used to annotate a model such that the mypy plugin may turn this into
    a union of all the default querysets for all the concrete children of the
    specified abstract model class, or of that model when it is a concrete model
    """
