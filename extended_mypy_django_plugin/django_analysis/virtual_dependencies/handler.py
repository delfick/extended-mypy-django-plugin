import abc
import dataclasses
import pathlib
import tempfile
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Generic

from typing_extensions import Self

from .. import discovery, hasher, project, protocols
from . import dependency, report
from .folder import VirtualDependencyGenerator, VirtualDependencyInstaller
from .namer import VirtualDependencyNamer


@dataclasses.dataclass(frozen=True, kw_only=True)
class VirtualDependencyHandler(
    Generic[protocols.T_Project, protocols.T_VirtualDependency, protocols.T_Report], abc.ABC
):
    hasher: protocols.Hasher
    discovered: protocols.Discovered[protocols.T_Project]

    @classmethod
    def create(cls, *, project_root: pathlib.Path, django_settings_module: str) -> Self:
        return cls(
            hasher=cls.make_hasher(),
            discovered=cls.discover_project(
                project_root=project_root, django_settings_module=django_settings_module
            ),
        )

    @classmethod
    def create_report(
        cls,
        *,
        project_root: pathlib.Path,
        django_settings_module: str,
        virtual_deps_destination: pathlib.Path,
    ) -> protocols.CombinedReport[protocols.T_Report]:
        return cls.create(
            project_root=project_root, django_settings_module=django_settings_module
        ).make_report(virtual_deps_destination=virtual_deps_destination)

    def make_report(
        self, virtual_deps_destination: pathlib.Path
    ) -> protocols.CombinedReport[protocols.T_Report]:
        installed_apps_hash = self.hash_installed_apps()
        virtual_namespace = self.get_virtual_namespace()
        virtual_dependency_namer = self.make_virtual_dependency_namer(
            virtual_namespace=virtual_namespace
        )
        virtual_dependency_maker = self.virtual_dependency_maker(
            installed_apps_hash=installed_apps_hash,
            virtual_dependency_namer=virtual_dependency_namer,
            make_differentiator=self.interface_differentiator,
        )
        all_virtual_dependencies = self.get_virtual_dependencies(
            virtual_dependency_maker=virtual_dependency_maker
        )
        report_factory = self.make_report_factory()
        virtual_dependency_installer = self.make_virtual_dependency_installer(
            all_virtual_dependencies=all_virtual_dependencies
        )

        with tempfile.TemporaryDirectory() as scratch_root:
            return virtual_dependency_installer(
                scratch_root=pathlib.Path(scratch_root),
                destination=virtual_deps_destination,
                virtual_namespace=virtual_namespace,
                report_factory=report_factory,
            )

    @classmethod
    @abc.abstractmethod
    def discover_project(
        cls, *, project_root: pathlib.Path, django_settings_module: str
    ) -> protocols.Discovered[protocols.T_Project]: ...

    @abc.abstractmethod
    def make_report_factory(
        self,
    ) -> protocols.ReportFactory[protocols.T_VirtualDependency, protocols.T_Report]: ...

    @abc.abstractmethod
    def virtual_dependency_maker(
        self,
        *,
        installed_apps_hash: str,
        virtual_dependency_namer: protocols.VirtualDependencyNamer,
        make_differentiator: Callable[[], str],
    ) -> protocols.VirtualDependencyMaker[protocols.T_Project, protocols.T_VirtualDependency]: ...

    def make_virtual_dependency_installer(
        self,
        *,
        all_virtual_dependencies: protocols.VirtualDependencyMap[protocols.T_VirtualDependency],
    ) -> protocols.VirtualDependencyInstaller[protocols.T_VirtualDependency, protocols.T_Report]:
        return VirtualDependencyInstaller(virtual_dependencies=all_virtual_dependencies)

    @classmethod
    def make_hasher(cls) -> protocols.Hasher:
        return hasher.adler32_hash

    def interface_differentiator(self) -> str:
        return str(time.time()).replace(".", "_")

    def hash_installed_apps(self) -> str:
        return self.hasher(
            *(app.encode() for app in self.discovered.loaded_project.settings.INSTALLED_APPS)
        )

    def make_virtual_dependency_namer(
        self, *, virtual_namespace: protocols.ImportPath
    ) -> protocols.VirtualDependencyNamer:
        return VirtualDependencyNamer(namespace=virtual_namespace, hasher=self.hasher)

    def get_virtual_namespace(self) -> protocols.ImportPath:
        return discovery.ImportPath("__virtual_extended_mypy_django_plugin_deps__")

    def get_virtual_dependencies(
        self,
        *,
        virtual_dependency_maker: protocols.VirtualDependencyMaker[
            protocols.T_Project, protocols.T_VirtualDependency
        ],
    ) -> protocols.VirtualDependencyMap[protocols.T_VirtualDependency]:
        return VirtualDependencyGenerator(virtual_dependency_maker=virtual_dependency_maker)(
            discovered_project=self.discovered
        )


if TYPE_CHECKING:
    C_VirtualDependencyHandler = VirtualDependencyHandler[
        project.C_Project, dependency.C_VirtualDependency, report.C_Report
    ]

    _VDH: protocols.P_VirtualDependencyHandler = VirtualDependencyHandler[
        protocols.P_Project, protocols.P_VirtualDependency, protocols.P_Report
    ].create_report

    _CVDH: protocols.VirtualDependencyHandler[report.C_Report] = (
        C_VirtualDependencyHandler.create_report
    )
