import abc
import dataclasses
import pathlib
import tempfile
import time
from typing import TYPE_CHECKING, Generic

from typing_extensions import Self

from ...version import VERSION
from .. import discovery, hasher, project, protocols
from . import dependency, report
from .folder import VirtualDependencyGenerator, VirtualDependencyInstaller
from .namer import VirtualDependencyNamer


@dataclasses.dataclass(frozen=True, kw_only=True)
class VirtualDependencyHandler(
    Generic[protocols.T_Project, protocols.T_VirtualDependency, protocols.T_Report], abc.ABC
):
    """
    This brings together the project, virtual dependencies and the report such that given a project
    we can generate the virtual dependencies and a relevant report.

    These three things are all customizable and this class is an orchestration mechanism.

    Usage is via the "create" and "create_report" classmethods, where "create_report" is a shortcut
    to saying ``Handler.create().make_report()``.

    And "create" is a shortcut to creating an instance of the Handler with the hasher and project
    found using the "make_hasher" and "make_project" classmethods on this class.
    """

    hasher: protocols.Hasher
    discovered: protocols.Discovered[protocols.T_Project]

    @classmethod
    def create(cls, *, project_root: pathlib.Path, django_settings_module: str) -> Self:
        return cls(
            hasher=cls.make_hasher(),
            discovered=(
                cls.make_project(
                    project_root=project_root, django_settings_module=django_settings_module
                )
                .load_project()
                .perform_discovery()
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
        """
        The main orchestration to create the virtual dependencies and the final
        combined report.

        There are a number of customization points that this class has hooks for so that
        this method remains generic to how virtual dependencies are represented on disk and
        in the report, as well as what information goes into them, and how and where they
        are written to disk.
        """
        installed_apps_hash = self.hash_installed_apps()
        settings_types_hash = self.hash_settings_types()
        virtual_namespace = self.get_virtual_namespace()
        virtual_dependency_namer = self.make_virtual_dependency_namer(
            virtual_namespace=virtual_namespace
        )
        virtual_dependency_maker = self.virtual_dependency_maker(
            virtual_dependency_namer=virtual_dependency_namer
        )
        all_virtual_dependencies = self.get_virtual_dependencies(
            virtual_dependency_maker=virtual_dependency_maker
        )
        report_factory = self.make_report_factory(installed_apps_hash=installed_apps_hash)
        project_version = f"plugin:{VERSION}:installed_apps:{installed_apps_hash}|settings_types:{settings_types_hash}"
        virtual_dependency_installer = self.make_virtual_dependency_installer(
            virtual_dependency_namer=virtual_dependency_namer,
            project_version=project_version,
            all_virtual_dependencies=all_virtual_dependencies,
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
    def make_project(
        cls, *, project_root: pathlib.Path, django_settings_module: str
    ) -> protocols.T_Project: ...

    @abc.abstractmethod
    def make_report_factory(
        self, *, installed_apps_hash: str
    ) -> protocols.ReportFactory[protocols.T_VirtualDependency, protocols.T_Report]: ...

    @abc.abstractmethod
    def virtual_dependency_maker(
        self, *, virtual_dependency_namer: protocols.VirtualDependencyNamer
    ) -> protocols.VirtualDependencyMaker[protocols.T_Project, protocols.T_VirtualDependency]: ...

    def make_virtual_dependency_installer(
        self,
        *,
        project_version: str,
        virtual_dependency_namer: protocols.VirtualDependencyNamer,
        all_virtual_dependencies: protocols.VirtualDependencyMap[protocols.T_VirtualDependency],
    ) -> protocols.VirtualDependencyInstaller[protocols.T_VirtualDependency, protocols.T_Report]:
        return VirtualDependencyInstaller(
            virtual_dependency_namer=virtual_dependency_namer,
            project_version=project_version,
            virtual_dependencies=all_virtual_dependencies,
        )

    @classmethod
    def make_hasher(cls) -> protocols.Hasher:
        return hasher.adler32_hash

    def interface_differentiator(self) -> str:
        return str(time.time()).replace(".", "_")

    def hash_installed_apps(self) -> str:
        return self.hasher(
            *(app.encode() for app in self.discovered.loaded_project.settings.INSTALLED_APPS)
        )

    def hash_settings_types(self) -> str:
        return self.hasher(
            *(f"{k}:{v}".encode() for k, v in sorted(self.discovered.settings_types.items()))
        )

    def make_virtual_dependency_namer(
        self, *, virtual_namespace: protocols.ImportPath
    ) -> protocols.VirtualDependencyNamer:
        return VirtualDependencyNamer(namespace=virtual_namespace, hasher=self.hasher)

    def get_virtual_namespace(self) -> protocols.ImportPath:
        return discovery.ImportPath("__virtual_extended_mypy_django_plugin_report__")

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
