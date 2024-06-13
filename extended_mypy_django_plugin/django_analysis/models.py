from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Protocol, cast

from django.db import models
from typing_extensions import Self

from extended_mypy_django_plugin.django_analysis import protocols


class FieldCreator(Protocol):
    def __call__(
        self, *, model_import_path: protocols.ImportPath, field: protocols.DjangoField
    ) -> protocols.Field: ...


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
            module_import_path=protocols.ImportPath(model.__module__),
            import_path=(
                model_import_path := protocols.ImportPath(
                    f"{model.__module__}.{model.__qualname__}"
                )
            ),
            is_abstract=model._meta.abstract,
            default_custom_queryset=(
                None
                if (dm := model._meta.default_manager) is None
                else (
                    None
                    if (
                        (qs := getattr(dm, "_queryset_class", models.QuerySet)) is models.QuerySet
                        or not isinstance(qs, type)
                    )
                    else protocols.ImportPath(f"{qs.__module__}.{qs.__qualname__}")
                )
            ),
            all_fields={
                field.name: field_creator(model_import_path=model_import_path, field=field)
                for field in model._meta.get_fields(include_parents=True, include_hidden=True)
            },
        )

    model_name: str
    module_import_path: protocols.ImportPath
    import_path: protocols.ImportPath
    is_abstract: bool
    default_custom_queryset: protocols.ImportPath | None
    all_fields: protocols.FieldsMap


if TYPE_CHECKING:
    _M: protocols.Model = cast(Model, None)
