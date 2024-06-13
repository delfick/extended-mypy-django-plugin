from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Protocol, cast

from django.db import models
from typing_extensions import Self

from extended_mypy_django_plugin.django_analysis import protocols


class FieldCreator(Protocol):
    def __call__(
        self, *, model_import_path: protocols.ImportPath, field: models.fields.Field[Any, Any]
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
        is_abstract: bool = False
        default_custom_queryset: protocols.ImportPath | None = None
        defined_fields: protocols.FieldsMap = {}

        return cls(
            model_name=model.__class__.__qualname__,
            module_import_path=protocols.ImportPath(model.__module__),
            import_path=protocols.ImportPath(f"{model.__module__}.{model.__class__.__qualname__}"),
            is_abstract=is_abstract,
            default_custom_queryset=default_custom_queryset,
            defined_fields=defined_fields,
        )

    model_name: str
    module_import_path: protocols.ImportPath
    import_path: protocols.ImportPath
    is_abstract: bool
    default_custom_queryset: protocols.ImportPath | None
    defined_fields: protocols.FieldsMap


if TYPE_CHECKING:
    _M: protocols.Model = cast(Model, None)
