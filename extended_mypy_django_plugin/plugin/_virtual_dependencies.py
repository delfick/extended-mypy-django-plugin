import abc
import functools
from collections.abc import Callable
from typing import TYPE_CHECKING, Generic, TypeVar

from ..django_analysis import project, protocols, virtual_dependencies
from ..django_analysis.protocols import (
    VirtualDependencyHandler as VirtualDependencyHandlerProtocol,
)

Report = virtual_dependencies.Report
T_Report = TypeVar("T_Report", bound=Report)


class DefaultVirtualDependencyHandler(
    Generic[protocols.T_Project],
    virtual_dependencies.VirtualDependencyHandler[
        protocols.T_Project,
        virtual_dependencies.VirtualDependency[protocols.T_Project],
        Report,
    ],
    abc.ABC,
):
    def make_report_factory(
        self,
    ) -> protocols.ReportFactory[
        virtual_dependencies.VirtualDependency[protocols.T_Project], Report
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
    "DefaultVirtualDependencyHandler",
    "T_Report",
    "Report",
]

if TYPE_CHECKING:
    C_VirtualDependencyHandler = DefaultVirtualDependencyHandler[project.C_Project]

    _DVDH: VirtualDependencyHandlerProtocol[Report] = DefaultVirtualDependencyHandler[
        protocols.P_Project
    ].create_report
    _CDVDH: VirtualDependencyHandlerProtocol[Report] = C_VirtualDependencyHandler.create_report
