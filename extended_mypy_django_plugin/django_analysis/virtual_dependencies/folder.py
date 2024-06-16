import dataclasses
import pathlib
from typing import TYPE_CHECKING, Generic, cast

from .. import project, protocols
from . import dependency, report


@dataclasses.dataclass(frozen=True, kw_only=True)
class VirtualDependencyGenerator(
    Generic[protocols.T_Project, protocols.T_CO_VirtualDependency, protocols.T_Report]
):
    report_factory: protocols.ReportFactory[protocols.T_CO_VirtualDependency, protocols.T_Report]
    virtual_dependency_maker: protocols.VirtualDependencyMaker[
        protocols.T_Project, protocols.T_CO_VirtualDependency
    ]

    def __call__(
        self, *, discovered_project: protocols.Discovered[protocols.T_Project]
    ) -> protocols.GeneratedVirtualDependencies[
        protocols.T_CO_VirtualDependency, protocols.T_Report
    ]:
        return GeneratedVirtualDependencies(
            report_factory=self.report_factory,
            virtual_dependencies={
                import_path: self.virtual_dependency_maker(
                    discovered_project=discovered_project, module=module
                )
                for import_path, module in discovered_project.installed_models_modules.items()
            },
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class GeneratedVirtualDependencies(Generic[protocols.T_VirtualDependency, protocols.T_Report]):
    report_factory: protocols.ReportFactory[protocols.T_VirtualDependency, protocols.T_Report]
    virtual_dependencies: protocols.VirtualDependencyMap[protocols.T_VirtualDependency]

    def install(
        self, *, scratch_root: pathlib.Path, destination: pathlib.Path
    ) -> protocols.T_Report:
        return self.report_factory.report_maker()


if TYPE_CHECKING:
    C_VirtualDependencyGenerator = VirtualDependencyGenerator[
        project.C_Project, dependency.C_VirtualDependency, report.C_Report
    ]
    C_GeneratedVirtualDependencies = GeneratedVirtualDependencies[
        dependency.C_VirtualDependency, report.C_Report
    ]

    _VDN: protocols.P_VirtualDependencyGenerator = cast(
        VirtualDependencyGenerator[
            protocols.P_Project, protocols.P_VirtualDependency, protocols.P_Report
        ],
        None,
    )
    _GVD: protocols.P_GeneratedVirtualDependencies = cast(
        GeneratedVirtualDependencies[protocols.P_VirtualDependency, protocols.P_Report], None
    )

    _CVDN: protocols.VirtualDependencyGenerator[
        project.C_Project, dependency.C_VirtualDependency, report.C_Report
    ] = cast(C_VirtualDependencyGenerator, None)
    _CGVD: protocols.GeneratedVirtualDependencies[
        dependency.C_VirtualDependency, report.C_Report
    ] = cast(C_GeneratedVirtualDependencies, None)
