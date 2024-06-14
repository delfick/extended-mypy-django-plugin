import dataclasses
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Generic, cast

from typing_extensions import Self

from .. import project, protocols


@dataclasses.dataclass
class VirtualDependencySummary:
    virtual_dependency_name: protocols.ImportPath
    module_import_path: protocols.ImportPath
    installed_apps_hash: str | None
    deps_hash: str | None


@dataclasses.dataclass
class VirtualDependency(Generic[protocols.T_Project]):
    module: protocols.Module
    interface_differentiator: str
    summary: VirtualDependencySummary
    all_related_models: Sequence[protocols.ImportPath]
    concrete_annotations: Mapping[protocols.ImportPath, Sequence[protocols.Model]]

    @classmethod
    def make(
        cls,
        *,
        discovered_project: protocols.Discovered[protocols.T_Project],
        module: protocols.Module,
    ) -> Self:
        return None  # type: ignore[return-value]


if TYPE_CHECKING:
    C_VirtualDependency = VirtualDependency[project.C_Project]

    _VD: protocols.VirtualDependency = cast(VirtualDependency[protocols.P_Project], None)
    _VDS: protocols.VirtualDependencySummary = cast(VirtualDependencySummary, None)
    _VDM: protocols.P_VirtualDependencyMaker = VirtualDependency[protocols.P_Project].make

    _CVDM: protocols.VirtualDependencyMaker[project.C_Project, C_VirtualDependency] = (
        VirtualDependency[project.C_Project].make
    )
