from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, cast

from django.db import models
from typing_extensions import Self

from extended_mypy_django_plugin.django_analysis import ImportPath, protocols


class FieldCreator(Protocol):
    def __call__(
        self, *, model_import_path: protocols.ImportPath, field: protocols.DjangoField
    ) -> protocols.Field: ...


def _find_default_custom_queryset(model: type[models.Model]) -> protocols.ImportPath | None:
    """
    Given a model, find the import path to the custom default queryset associated with that model
    if it has one.
    """
    if (default_manager := model._meta.default_manager) is None:
        # No custom default queryset if there is no default manager
        return None

    if (qs := getattr(default_manager, "_queryset_class", models.QuerySet)) is models.QuerySet:
        # default queryset isn't interesting to us!
        return None

    if not isinstance(qs, type):
        # If the queryset isn't a type, then it's unlikely we can find an import path to it
        return None

    return ImportPath.from_cls(qs)


@dataclasses.dataclass(frozen=True, kw_only=True)
class Model:
    @classmethod
    def create(
        cls,
        *,
        field_creator: FieldCreator,
        model: type[models.Model],
    ) -> Self:
        return cls(
            model_name=model.__qualname__,
            module_import_path=ImportPath.cls_module(model),
            import_path=(model_import_path := ImportPath.from_cls(model)),
            is_abstract=model._meta.abstract,
            default_custom_queryset=_find_default_custom_queryset(model),
            all_fields={
                # We want to know the concrete set of models, and we include hidden fields
                # So that we can see all related models later on
                field.name: field_creator(model_import_path=model_import_path, field=field)
                for field in model._meta.get_fields(include_parents=True, include_hidden=True)
            },
            models_in_mro=[
                # Only care about parent models that are themselves other models and aren't
                # the base django Model class or the model being looked at
                ImportPath.from_cls(m)
                for m in model.__mro__
                if issubclass(m, models.Model) and m not in (models.Model, model)
            ],
        )

    model_name: str
    module_import_path: protocols.ImportPath
    import_path: protocols.ImportPath
    is_abstract: bool
    default_custom_queryset: protocols.ImportPath | None
    all_fields: protocols.FieldsMap
    models_in_mro: Sequence[protocols.ImportPath]


if TYPE_CHECKING:
    _M: protocols.Model = cast(Model, None)
