import dataclasses
import pathlib
from typing import TYPE_CHECKING, Generic, cast

from .. import project, protocols
from . import dependency, report


@dataclasses.dataclass(frozen=True, kw_only=True)
class VirtualDependencyGenerator(Generic[protocols.T_Project, protocols.T_VirtualDependency]):
    virtual_dependency_maker: protocols.VirtualDependencyMaker[
        protocols.T_Project, protocols.T_VirtualDependency
    ]

    def __call__(
        self, *, discovered_project: protocols.Discovered[protocols.T_Project]
    ) -> protocols.VirtualDependencyMap[protocols.T_VirtualDependency]:
        return {
            import_path: self.virtual_dependency_maker(
                discovered_project=discovered_project, module=module
            )
            for import_path, module in discovered_project.installed_models_modules.items()
        }


@dataclasses.dataclass(frozen=True, kw_only=True)
class VirtualDependencyInstaller(Generic[protocols.T_VirtualDependency, protocols.T_Report]):
    virtual_dependencies: protocols.VirtualDependencyMap[protocols.T_VirtualDependency]

    def __call__(
        self,
        *,
        scratch_root: pathlib.Path,
        destination: pathlib.Path,
        report_factory: protocols.ReportFactory[protocols.T_VirtualDependency, protocols.T_Report],
    ) -> protocols.T_Report:
        return report_factory.report_maker()


if TYPE_CHECKING:
    C_VirtualDependencyGenerator = VirtualDependencyGenerator[
        project.C_Project, dependency.C_VirtualDependency
    ]
    C_VirtualDependencyInstaller = VirtualDependencyInstaller[
        dependency.C_VirtualDependency, report.C_Report
    ]

    _VDN: protocols.P_VirtualDependencyGenerator = cast(
        VirtualDependencyGenerator[protocols.P_Project, protocols.P_VirtualDependency],
        None,
    )
    _GVD: protocols.P_VirtualDependencyInstaller = cast(
        VirtualDependencyInstaller[protocols.P_VirtualDependency, protocols.P_Report], None
    )

    _CVDN: protocols.VirtualDependencyGenerator[
        project.C_Project, dependency.C_VirtualDependency
    ] = cast(C_VirtualDependencyGenerator, None)
    _CGVD: protocols.VirtualDependencyInstaller[
        dependency.C_VirtualDependency, report.C_Report
    ] = cast(C_VirtualDependencyInstaller, None)
