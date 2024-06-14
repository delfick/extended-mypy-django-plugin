import dataclasses
import pathlib
from typing import TYPE_CHECKING, Generic, cast

from .. import project, protocols
from . import dependency


@dataclasses.dataclass(frozen=True, kw_only=True)
class VirtualDependencyFolder(Generic[protocols.T_Project, protocols.T_CO_VirtualDependency]):
    discovered_project: protocols.Discovered[protocols.T_Project]
    virtual_dependency_maker: protocols.VirtualDependencyMaker[
        protocols.T_Project, protocols.T_CO_VirtualDependency
    ]

    def generate(
        self, scratch_root: pathlib.Path
    ) -> protocols.GeneratedVirtualDependencies[protocols.T_CO_VirtualDependency]:
        return GeneratedVirtualDependencies(virtual_dependencies={}, root_location=scratch_root)


@dataclasses.dataclass(frozen=True, kw_only=True)
class GeneratedVirtualDependencies(Generic[protocols.T_CO_VirtualDependency]):
    virtual_dependencies: protocols.VirtualDependencyMap[protocols.T_CO_VirtualDependency]
    root_location: pathlib.Path

    def install(self, destination: pathlib.Path) -> None:
        pass


if TYPE_CHECKING:
    C_VirtualDependencyFolder = VirtualDependencyFolder[
        project.C_Project, dependency.C_VirtualDependency
    ]
    C_GeneratedVirtualDependencies = GeneratedVirtualDependencies[dependency.C_VirtualDependency]

    _VDN: protocols.P_VirtualDependencyFolder = cast(
        VirtualDependencyFolder[protocols.P_Project, protocols.P_VirtualDependency], None
    )
    _GVD: protocols.P_GeneratedVirtualDependencies = cast(
        GeneratedVirtualDependencies[protocols.P_VirtualDependency], None
    )

    _CVDN: protocols.VirtualDependencyFolder[project.C_Project, dependency.C_VirtualDependency] = (
        cast(C_VirtualDependencyFolder, None)
    )
    _CGVD: protocols.GeneratedVirtualDependencies[dependency.C_VirtualDependency] = cast(
        C_GeneratedVirtualDependencies, None
    )
