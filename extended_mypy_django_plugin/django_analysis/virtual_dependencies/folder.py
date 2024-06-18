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
        virtual_namespace: protocols.ImportPath,
        report_factory: protocols.ReportFactory[protocols.T_VirtualDependency, protocols.T_Report],
    ) -> protocols.CombinedReport[protocols.T_Report]:
        reports: list[protocols.T_Report] = []
        for written in report_factory.deploy_scribes(self.virtual_dependencies):
            report_factory.report_installer.write_report(
                virtual_import_path=written.virtual_import_path,
                summary_hash=written.summary_hash,
                content=written.content,
                scratch_root=scratch_root,
            )
            reports.append(written.report)

        report_factory.report_installer.install_reports(
            scratch_root=scratch_root,
            destination=destination,
            virtual_namespace=virtual_namespace,
        )
        return report_factory.report_combiner_maker(reports=reports).combine(version="__version__")


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
