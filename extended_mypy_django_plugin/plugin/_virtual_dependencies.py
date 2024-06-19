import abc
import functools
from collections.abc import Callable, Sequence, Set
from typing import TYPE_CHECKING, Generic, Protocol, TypeVar

from ..django_analysis import project, protocols, virtual_dependencies
from ..django_analysis.protocols import (
    CombinedReport as CombinedReportProtocol,
)
from ..django_analysis.protocols import (
    VirtualDependencyHandler as VirtualDependencyHandlerProtocol,
)


class ReportProtocol(Protocol):
    def additional_deps(
        self,
        *,
        file_import_path: str,
        imports: Set[str],
        super_deps: Sequence[tuple[int, str, int]],
        django_settings_module: str,
    ) -> Sequence[tuple[int, str, int]]:
        """
        This is used to add to the result for the get_additional_deps mypy hook.

        It takes the import path for the file being looked at, any additional deps that have already
        been determined for the file, the imports the file contains as a list of full imports,
        and the import path of the django settings module.

        It must return the full set of additional deps the mypy plugin should use for this file
        """

    def is_model_installed(self, *, import_path: str) -> bool:
        """
        Used to determine if a model is installed in this django project
        """


T_Report = TypeVar("T_Report", bound=ReportProtocol)


class DefaultVirtualDependencyHandler(
    Generic[protocols.T_Project],
    virtual_dependencies.VirtualDependencyHandler[
        protocols.T_Project,
        virtual_dependencies.VirtualDependency[protocols.T_Project],
        virtual_dependencies.Report,
    ],
    abc.ABC,
):
    def make_report_factory(
        self,
    ) -> protocols.ReportFactory[
        virtual_dependencies.VirtualDependency[protocols.T_Project], virtual_dependencies.Report
    ]:
        return virtual_dependencies.make_report_factory(hasher=self.hasher)

    def virtual_dependency_maker(
        self,
        *,
        installed_apps_hash: str,
        virtual_dependency_namer: protocols.VirtualDependencyNamer,
        make_differentiator: Callable[[], str],
    ) -> protocols.VirtualDependencyMaker[
        protocols.T_Project, virtual_dependencies.VirtualDependency[protocols.T_Project]
    ]:
        return functools.partial(
            virtual_dependencies.VirtualDependency.create,
            discovered_project=self.discovered,
            virtual_dependency_namer=virtual_dependency_namer,
            installed_apps_hash=installed_apps_hash,
            make_differentiator=make_differentiator,
        )


__all__ = [
    "VirtualDependencyHandlerProtocol",
    "CombinedReportProtocol",
    "ReportProtocol",
    "DefaultVirtualDependencyHandler",
    "T_Report",
]

if TYPE_CHECKING:
    C_VirtualDependencyHandler = DefaultVirtualDependencyHandler[project.C_Project]

    _DVDH: VirtualDependencyHandlerProtocol[virtual_dependencies.Report] = (
        DefaultVirtualDependencyHandler[protocols.P_Project].create_report
    )
    _CDVDH: VirtualDependencyHandlerProtocol[virtual_dependencies.Report] = (
        C_VirtualDependencyHandler.create_report
    )
