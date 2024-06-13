from __future__ import annotations

import dataclasses
from collections.abc import Set
from typing import TYPE_CHECKING, cast

from typing_extensions import Self

from extended_mypy_django_plugin.django_analysis import protocols


@dataclasses.dataclass(frozen=True, kw_only=True)
class Field:
    @classmethod
    def create(
        cls, *, model_import_path: protocols.ImportPath, field: protocols.DjangoField
    ) -> Self:
        field_type: protocols.ImportPath = protocols.ImportPath("")
        directly_related_models: Set[protocols.ImportPath] = set()
        return cls(
            model_import_path=model_import_path,
            field_type=field_type,
            directly_related_models=directly_related_models,
        )

    model_import_path: protocols.ImportPath
    field_type: protocols.ImportPath
    directly_related_models: Set[protocols.ImportPath]


if TYPE_CHECKING:
    _M: protocols.Field = cast(Field, None)
