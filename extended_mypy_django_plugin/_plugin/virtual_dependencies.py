import abc
import dataclasses
import functools
import pathlib
from typing import TYPE_CHECKING, Generic

from ..django_analysis import Project, discovery, project, virtual_dependencies
from ..django_analysis import protocols as d_protocols
from . import protocols as p_protocols


@dataclasses.dataclass(frozen=True, kw_only=True)
class VirtualDependencyHandlerBase(
    Generic[d_protocols.T_Project],
    virtual_dependencies.VirtualDependencyHandler[
        d_protocols.T_Project,
        virtual_dependencies.VirtualDependency[d_protocols.T_Project],
        virtual_dependencies.Report,
    ],
    abc.ABC,
):
    def get_report_maker(self) -> d_protocols.ReportMaker[virtual_dependencies.Report]:
        return virtual_dependencies.Report

    def make_report_factory(
        self, *, installed_apps_hash: str
    ) -> d_protocols.ReportFactory[
        virtual_dependencies.VirtualDependency[d_protocols.T_Project], virtual_dependencies.Report
    ]:
        return virtual_dependencies.make_report_factory(
            hasher=self.hasher,
            report_maker=self.get_report_maker(),
            installed_apps_hash=installed_apps_hash,
            make_differentiator=self.interface_differentiator,
        )

    def virtual_dependency_maker(
        self, *, virtual_dependency_namer: d_protocols.VirtualDependencyNamer
    ) -> d_protocols.VirtualDependencyMaker[
        d_protocols.T_Project, virtual_dependencies.VirtualDependency[d_protocols.T_Project]
    ]:
        return functools.partial(
            virtual_dependencies.VirtualDependency.create,
            discovered_project=self.discovered,
            virtual_dependency_namer=virtual_dependency_namer,
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class VirtualDependencyHandler(VirtualDependencyHandlerBase[Project]):
    @classmethod
    def make_project(cls, *, project_root: pathlib.Path, django_settings_module: str) -> Project:
        return Project(
            root_dir=project_root,
            additional_sys_path=[str(project_root)],
            env_vars={"DJANGO_SETTINGS_MODULE": django_settings_module},
            discovery=discovery.Discovery(),
        )


if TYPE_CHECKING:
    P_VirtualDependencyHandler = VirtualDependencyHandlerBase[project.C_Project]
    C_VirtualDependencyHandler = VirtualDependencyHandler

    _DVDH: p_protocols.P_VirtualDependencyHandler = VirtualDependencyHandlerBase[
        d_protocols.P_Project
    ].create_report
    _CDVDH: p_protocols.VirtualDependencyHandler[virtual_dependencies.Report] = (
        C_VirtualDependencyHandler.create_report
    )
