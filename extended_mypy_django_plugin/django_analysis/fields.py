from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, cast

from django.db import models
from typing_extensions import Self

from extended_mypy_django_plugin.django_analysis import protocols


@dataclasses.dataclass(frozen=True, kw_only=True)
class Field:
    @classmethod
    def create(
        cls, *, model_import_path: protocols.ImportPath, field: protocols.DjangoField
    ) -> Self:
        return cls(
            model_import_path=model_import_path,
            field_type=protocols.ImportPath(
                f"{field.__class__.__module__}.{field.__class__.__qualname__}"
            ),
            related_model=(
                protocols.ImportPath(f"{related.__module__}.{related.__qualname__}")
                if (
                    isinstance((related := field.related_model), type)
                    and issubclass(related, models.Model)
                    and not related._meta.auto_created
                )
                else None
            ),
        )

    model_import_path: protocols.ImportPath
    field_type: protocols.ImportPath
    related_model: protocols.ImportPath | None


if TYPE_CHECKING:
    _M: protocols.Field = cast(Field, None)
