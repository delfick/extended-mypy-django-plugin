import dataclasses
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, cast

from .. import protocols


@dataclasses.dataclass
class VirtualDependencySummary:
    virtual_dependency_name: protocols.ImportPath
    module_import_path: protocols.ImportPath
    installed_apps_hash: str | None
    deps_hash: str | None


@dataclasses.dataclass
class VirtualDependency:
    module: protocols.Module
    interface_differentiator: str
    summary: VirtualDependencySummary
    all_related_models: Sequence[protocols.ImportPath]
    concrete_annotations: Mapping[protocols.ImportPath, Sequence[protocols.Model]]


if TYPE_CHECKING:
    _VD: protocols.VirtualDependency = cast(VirtualDependency, None)
    _VDS: protocols.VirtualDependencySummary = cast(VirtualDependencySummary, None)
