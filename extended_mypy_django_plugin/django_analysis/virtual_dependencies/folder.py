import dataclasses
import functools
import os
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
    project_version: str
    virtual_dependencies: protocols.VirtualDependencyMap[protocols.T_VirtualDependency]
    virtual_dependency_namer: protocols.VirtualDependencyNamer

    def __call__(
        self,
        *,
        scratch_root: pathlib.Path,
        destination: pathlib.Path,
        virtual_namespace: protocols.ImportPath,
        report_factory: protocols.ReportFactory[protocols.T_VirtualDependency, protocols.T_Report],
    ) -> protocols.CombinedReport[protocols.T_Report]:
        # Determine what would be written to represent the virtual dependencies
        # And gather each report so we can later combine them into the final report
        reports: list[protocols.T_Report] = []
        written_dependencies: list[protocols.RenderedVirtualDependency[protocols.T_Report]] = []
        for rendered in report_factory.deploy_scribes(self.virtual_dependencies):
            report_factory.report_installer.write_report(
                virtual_import_path=rendered.virtual_import_path,
                summary_hash=rendered.summary_hash,
                content=rendered.content,
                scratch_root=scratch_root,
            )
            written_dependencies.append(rendered)
            reports.append(rendered.report)

        # Install our on disk representation into the destination
        report_factory.report_installer.install_reports(
            scratch_root=scratch_root,
            destination=destination,
            virtual_namespace=virtual_namespace,
        )

        # Figure out a string representing the state of everything
        version = report_factory.determine_version(
            destination=destination,
            virtual_namespace=virtual_namespace,
            project_version=self.project_version,
            written_dependencies=written_dependencies,
        )

        # Create our final report
        return report_factory.report_combiner_maker(reports=reports).combine(
            version=version,
            write_empty_virtual_dep=functools.partial(
                self.write_empty_virtual_dep,
                destination=destination,
                report_factory=report_factory,
            ),
        )

    def write_empty_virtual_dep(
        self,
        *,
        module_import_path: protocols.ImportPath,
        destination: pathlib.Path,
        report_factory: protocols.ReportFactory[protocols.T_VirtualDependency, protocols.T_Report],
    ) -> protocols.ImportPath | None:
        """
        This method gets used at mypy time when we come across modules that we believe contains Django
        models that aren't included in settings.INSTALLED_APPS

        This is so when they are put into settings.INSTALLED_APPS, they don't also need to be modified
        to have a virtual dependency we can use to tell mypy to re-analyze the file on relevant changes
        in other parts of the codebase.
        """
        virtual_import_path = self.virtual_dependency_namer(module_import_path)
        location = destination / f'{virtual_import_path.replace(".", os.sep)}.py'
        if location.exists():
            return None

        content = report_factory.make_empty_virtual_dependency_content(
            module_import_path=module_import_path
        )
        if report_factory.report_installer.write_report(
            scratch_root=destination,
            virtual_import_path=virtual_import_path,
            content=content,
            summary_hash=False,
        ):
            return virtual_import_path
        else:
            return None


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
