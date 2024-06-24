from __future__ import annotations

import contextlib
import pathlib
from collections.abc import Hashable, Iterator, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal, NewType, Protocol, TypeVar, Union

from django.apps.registry import Apps
from django.conf import LazySettings
from django.db import models
from typing_extensions import Self

if TYPE_CHECKING:
    from django.contrib.contenttypes.fields import GenericForeignKey
    from django.db.models.fields.related import ForeignObjectRel

T_Project = TypeVar("T_Project", bound="P_Project")
T_VirtualDependency = TypeVar("T_VirtualDependency", bound="P_VirtualDependency")
T_CO_VirtualDependency = TypeVar(
    "T_CO_VirtualDependency", bound="P_VirtualDependency", covariant=True
)
T_COT_VirtualDependency = TypeVar(
    "T_COT_VirtualDependency", bound="P_VirtualDependency", contravariant=True
)

# The difference between Report and ReportUse is that the Report has an api used to build the report
# And ReportUse has no defined api to begin with, and is up to the thing using the report to define
# The api it wants. For this plugin that is defined in extended_mypy_django_plugin._virtual_dependencies
T_Report = TypeVar("T_Report", bound="P_Report")
T_CO_Report = TypeVar("T_CO_Report", bound="P_Report", covariant=True)
T_CO_ReportUse = TypeVar("T_CO_ReportUse", covariant=True)


ImportPath = NewType("ImportPath", str)
FieldsMap = Mapping[str, "Field"]
ModelMap = Mapping[ImportPath, "Model"]
ModelModulesMap = Mapping[ImportPath, "Module"]
ConcreteModelsMap = Mapping[ImportPath, Sequence["Model"]]
SettingsTypesMap = Mapping[str, str]
VirtualDependencyMap = Mapping[ImportPath, T_CO_VirtualDependency]
DjangoField = Union["models.fields.Field[Any, Any]", "ForeignObjectRel", "GenericForeignKey"]


class Hasher(Protocol):
    def __call__(self, *parts: bytes) -> str:
        """
        Given some strings, create a single hash of all that data
        """


class SettingsTypesDiscovery(Protocol[T_Project]):
    """
    Used to discovery the names and types of settings from a loaded project
    """

    def __call__(self, loaded_project: Loaded[T_Project], /) -> SettingsTypesMap: ...


class InstalledModelsDiscovery(Protocol[T_Project]):
    """
    Used to discover installed modules containing Django ORM models in a loaded project
    """

    def __call__(self, loaded_project: Loaded[T_Project], /) -> ModelModulesMap: ...


class ConcreteModelsDiscovery(Protocol[T_Project]):
    """
    Used to determine concrete models
    """

    def __call__(
        self, loaded_project: Loaded[T_Project], all_models: ModelMap, /
    ) -> ConcreteModelsMap: ...


class Discovery(Protocol[T_Project]):
    """
    A container for all the different discovery helpers
    """

    @property
    def discover_settings_types(self) -> SettingsTypesDiscovery[T_Project]:
        """
        Used to discover settings names and their types
        """

    @property
    def discover_installed_models(self) -> InstalledModelsDiscovery[T_Project]:
        """
        Used to discover installed modules containing Django ORM models
        """

    @property
    def discover_concrete_models(self) -> ConcreteModelsDiscovery[T_Project]:
        """
        Used to determine the concrete models for any model
        """


class Project(Protocol):
    """
    Represents a Django project to be analyzed
    """

    @property
    def root_dir(self) -> pathlib.Path:
        """
        Where the django project lives
        """

    @property
    def additional_sys_path(self) -> Sequence[str]:
        """
        Any additional paths that need to be added to sys.path
        """

    @property
    def env_vars(self) -> Mapping[str, str]:
        """
        Any additional environment variables needed to setup Django
        """

    @contextlib.contextmanager
    def setup_sys_path_and_env_vars(self) -> Iterator[None]:
        """
        Do necessary work to setup and cleanup changes to sys.path and os.environ to prepare
        for a django instantiation.
        """

    def load_project(self) -> Loaded[Self]:
        """
        Do necessary work to load Django into memory

        It is expected that an implementation will use self.setup_sys_path_and_env_vars to
        setup and cleanup required changes to sys.path and os.environ
        """


class Loaded(Protocol[T_Project]):
    """
    Represents a Django project that has been setup and loaded into memory
    """

    @property
    def project(self) -> T_Project:
        """
        The project that was loaded
        """

    @property
    def root_dir(self) -> pathlib.Path:
        """
        Where the django project lives
        """

    @property
    def env_vars(self) -> Mapping[str, str]:
        """
        Any additional environment variables that were used during Django setup
        """

    @property
    def settings(self) -> LazySettings:
        """
        The instantiated Django settings object
        """

    @property
    def apps(self) -> Apps:
        """
        The instantiated Django apps registry
        """

    def perform_discovery(self) -> Discovered[T_Project]:
        """
        Perform discovery of important information from the loaded Django project
        """


class Discovered(Protocol[T_Project]):
    @property
    def loaded_project(self) -> Loaded[T_Project]:
        """
        The loaded django project that was analyzed
        """

    @property
    def installed_models_modules(self) -> ModelModulesMap:
        """
        The known modules that contain installed Django Models
        """

    @property
    def all_models(self) -> ModelMap:
        """
        A map of all the models in the project
        """

    @property
    def installed_apps(self) -> list[str]:
        """
        The value of the settings.INSTALLED_APPS setting.
        """

    @property
    def settings_types(self) -> SettingsTypesMap:
        """
        All the django settings and a string representation of their type
        """

    @property
    def concrete_models(self) -> ConcreteModelsMap:
        """
        The map of models to their concrete equivalent
        """


class Module(Protocol, Hashable):
    """
    The models contained within a specific module
    """

    @property
    def import_path(self) -> ImportPath:
        """
        The full import path for this module
        """

    @property
    def defined_models(self) -> ModelMap:
        """
        A map of the installed models defined in this module
        """


class Model(Protocol, Hashable):
    """
    Represents the information contained by a Django model
    """

    @property
    def model_name(self) -> str:
        """
        The name of the class that this model represents
        """

    @property
    def module_import_path(self) -> ImportPath:
        """
        The import path to the module this model lives in
        """

    @property
    def import_path(self) -> ImportPath:
        """
        The full import path to this model
        """

    @property
    def is_abstract(self) -> bool:
        """
        Whether this model is abstract
        """

    @property
    def default_custom_queryset(self) -> ImportPath | None:
        """
        The import path to the default custom queryset for this model if one is defined
        """

    @property
    def all_fields(self) -> FieldsMap:
        """
        The fields associated with this model
        """

    @property
    def models_in_mro(self) -> Sequence[ImportPath]:
        """
        The import paths to the classes in the mro for this model

        As long as they:
        * aren't this model
        * not django.db.models.Model
        * are subclasses of django.db.models.Model
        """


class Field(Protocol):
    """
    Represents a single field on a model
    """

    @property
    def model_import_path(self) -> ImportPath:
        """
        The import path to the model this field is defined on
        """

    @property
    def field_type(self) -> ImportPath:
        """
        The import path to the type of object used to represent this type
        """

    @property
    def related_model(self) -> ImportPath | None:
        """
        The model that is related to this field if the field represents a relationship
        """


class VirtualDependencyNamer(Protocol):
    @property
    def namespace(self) -> ImportPath:
        """
        The namespace for the virtual dependencies
        """

    def __call__(self, module: ImportPath, /) -> ImportPath:
        """
        Return a deterministically determined name representing this module import path
        """


class VirtualDependencyMaker(Protocol[T_Project, T_CO_VirtualDependency]):
    """
    Responsible for generating a virtual dependency
    """

    def __call__(
        self, *, discovered_project: Discovered[T_Project], module: Module
    ) -> T_CO_VirtualDependency: ...


class VirtualDependencyGenerator(Protocol[T_Project, T_CO_VirtualDependency]):
    """
    Object that generates the objects representing the virtual dependencies
    """

    def __call__(
        self, *, discovered_project: Discovered[T_Project]
    ) -> VirtualDependencyMap[T_CO_VirtualDependency]:
        """
        Generate the virtual dependencies for this project
        """


class VirtualDependencyInstaller(Protocol[T_CO_VirtualDependency, T_Report]):
    """
    Used Install the virtual dependencies into their destination.

    Implementations should:

    * Build the reports in the scratch root before installing in the final destination
    * Clear out reports in the final destination that represent modules that don't exist anymore
    """

    def __call__(
        self,
        *,
        scratch_root: pathlib.Path,
        destination: pathlib.Path,
        virtual_namespace: ImportPath,
        report_factory: ReportFactory[T_CO_VirtualDependency, T_Report],
    ) -> CombinedReport[T_Report]: ...


class VirtualDependencySummary(Protocol):
    """
    Represents the different hashes that make up a full hash for a virtual dependency

    This is used to determine if the dependency has changed or not
    """

    @property
    def virtual_namespace(self) -> ImportPath:
        """
        The import path of the virtual dependencies
        """

    @property
    def virtual_import_path(self) -> ImportPath:
        """
        The import path the virtual dependency lives at
        """

    @property
    def module_import_path(self) -> ImportPath:
        """
        The import path to the real module this virtual dependency represents
        """

    @property
    def significant_info(self) -> Sequence[str]:
        """
        Strings representing significant information related to the module

        The idea is that changes in this list should warrant reloading Django in a fresh environment.
        """


class VirtualDependency(Protocol):
    """
    Represents the information held by a virtual dependency for a module
    """

    @property
    def module(self) -> Module:
        """
        The module represented by this virtual dependency
        """

    @property
    def summary(self) -> VirtualDependencySummary:
        """
        The parts that make up a final hash for this virtual dependency
        """

    @property
    def all_related_models(self) -> Sequence[ImportPath]:
        """
        All the models that are related to the module represented by this virtual dependency
        """

    @property
    def concrete_models(self) -> ConcreteModelsMap:
        """
        The models known by this module and their concrete children
        """


class Report(Protocol):
    """
    A report of information that can be used by the mypy plugin to easily get
    information from the virtual dependencies
    """

    def register_module(
        self,
        *,
        module_import_path: ImportPath,
        virtual_import_path: ImportPath,
    ) -> None:
        """
        Register a module to it's virtual path
        """

    def register_model(
        self,
        *,
        model_import_path: ImportPath,
        virtual_import_path: ImportPath,
        concrete_name: str,
        concrete_queryset_name: str,
        concrete_models: Sequence[Model],
    ) -> None:
        """
        Register details about a model
        """


class CombinedReport(Protocol[T_CO_ReportUse]):
    @property
    def version(self) -> str:
        """
        Used to determine a string that represents the state of the report
        such that the string changing indicates the state of the project changed
        """

    @property
    def report(self) -> T_CO_ReportUse:
        """
        The final combined report
        """

    def ensure_virtual_dependency(self, *, module_import_path: str) -> None:
        """
        Ensure this module has a virtual dependency if it should have one

        This is important because if a module contains models but isn't installed then when it is
        added to settings.INSTALLED_APPS without any changes, then we can't retrospectively give it
        a virtual dependency in get_additional_deps
        """


class ReportMaker(Protocol[T_CO_Report]):
    """
    Used to construct a report
    """

    def __call__(self) -> T_CO_Report: ...


class RenderedVirtualDependency(Protocol[T_CO_Report]):
    @property
    def content(self) -> str:
        """
        The string representing the content of the virtual dependency
        """

    @property
    def summary_hash(self) -> str | None:
        """
        A hash representing the state of the dependency

        This should be None if the module is not installed
        """

    @property
    def report(self) -> T_CO_Report:
        """
        The report representing the information in the content
        """

    @property
    def virtual_import_path(self) -> ImportPath:
        """
        The import path to this virtual dependency
        """


class VirtualDependencyScribe(Protocol[T_COT_VirtualDependency, T_CO_Report]):
    """
    Used to render the on disk representation of a virtual dependency along with the information
    contained in that dependency
    """

    def __call__(
        self,
        *,
        virtual_dependency: T_COT_VirtualDependency,
        all_virtual_dependencies: VirtualDependencyMap[T_COT_VirtualDependency],
    ) -> RenderedVirtualDependency[T_CO_Report]: ...


class MakeEmptyVirtualDepContent(Protocol):
    """
    Used to make the content that would go into a virtual dependency for an uninstalled module
    """

    def __call__(self, *, module_import_path: ImportPath) -> str: ...


class EmptyVirtualDepWriter(Protocol):
    """
    Used to generate the on disk representation of a virtual dependency for a module that has
    been determined as an uninstalled module with django models in it.

    It should return the import path for the created virtual import, or None if there was an
    existing virtual dependency or none was made
    """

    def __call__(self, *, module_import_path: ImportPath) -> ImportPath | None: ...


class ReportInstaller(Protocol):
    """
    Used to write reports to the file system
    """

    def write_report(
        self,
        *,
        scratch_root: pathlib.Path,
        virtual_import_path: ImportPath,
        content: str,
        summary_hash: str | Literal[False] | None,
    ) -> bool:
        """
        Write a single report to the scratch path

        If summary_hash is False, then only write if the virtual dep doesn't already exist

        Return whether a report was written
        """

    def install_reports(
        self,
        *,
        scratch_root: pathlib.Path,
        destination: pathlib.Path,
        virtual_namespace: ImportPath,
    ) -> None:
        """
        Copy reports from scratch_root into the destination when the reports on the destination
        are different to the reports in the scratch path.

        Also, delete redundant reports from destination
        """


class ReportCombiner(Protocol[T_CO_Report]):
    """
    Used to combine many reports into one
    """

    @property
    def reports(self) -> Sequence[T_CO_Report]:
        """
        The reports to combine
        """

    def combine(
        self, *, version: str, write_empty_virtual_dep: EmptyVirtualDepWriter
    ) -> CombinedReport[T_CO_Report]:
        """
        Return a single report that represents all the provided reports as one
        """


class ReportCombinerMaker(Protocol[T_Report]):
    """
    Used to create a report combiner
    """

    def __call__(self, *, reports: Sequence[T_Report]) -> ReportCombiner[T_Report]: ...


class ReportFactory(Protocol[T_COT_VirtualDependency, T_Report]):
    """
    Holds everything necessary for creating reports
    """

    @property
    def report_installer(self) -> ReportInstaller: ...

    @property
    def report_maker(self) -> ReportMaker[T_Report]: ...

    @property
    def report_combiner_maker(self) -> ReportCombinerMaker[T_Report]: ...

    @property
    def make_empty_virtual_dependency_content(self) -> MakeEmptyVirtualDepContent: ...

    def deploy_scribes(
        self, virtual_dependencies: VirtualDependencyMap[T_COT_VirtualDependency]
    ) -> Iterator[RenderedVirtualDependency[T_Report]]: ...

    def determine_version(
        self,
        *,
        destination: pathlib.Path,
        virtual_namespace: ImportPath,
        project_version: str,
        written_dependencies: Sequence[RenderedVirtualDependency[T_Report]],
    ) -> str:
        """
        Determine a version for the project, such that it only changes if the mypy daemon needs to be restarted
        """


class VirtualDependencyHandler(Protocol[T_CO_ReportUse]):
    """
    This is the interface required by the mypy plugin to create virtual dependencies and get a report
    of the information held by those virtual dependencies
    """

    def __call__(
        self,
        *,
        project_root: pathlib.Path,
        django_settings_module: str,
        virtual_deps_destination: pathlib.Path,
    ) -> CombinedReport[T_CO_ReportUse]: ...


if TYPE_CHECKING:
    P_Model = Model
    P_Field = Field
    P_Module = Module
    P_Hasher = Hasher
    P_Project = Project
    P_Loaded = Loaded[P_Project]
    P_Discovery = Discovery[P_Project]
    P_Discovered = Discovered[P_Project]
    P_SettingsTypesDiscovery = SettingsTypesDiscovery[P_Project]
    P_ConcreteModelsDiscovery = ConcreteModelsDiscovery[P_Project]
    P_InstalledModelsDiscovery = InstalledModelsDiscovery[P_Project]

    P_Report = Report
    P_VirtualDependency = VirtualDependency

    P_ReportMaker = ReportMaker[P_Report]
    P_ReportFactory = ReportFactory[P_VirtualDependency, P_Report]
    P_CombinedReport = CombinedReport[P_Report]
    P_ReportInstaller = ReportInstaller
    P_ReportCombiner = ReportCombiner[P_Report]
    P_ReportCombinerMaker = ReportCombinerMaker[P_Report]

    P_EmptyVirtualDepWriter = EmptyVirtualDepWriter
    P_MakeEmptyVirtualDepContent = MakeEmptyVirtualDepContent

    P_VirtualDependencyMaker = VirtualDependencyMaker[P_Project, P_VirtualDependency]
    P_VirtualDependencyNamer = VirtualDependencyNamer
    P_VirtualDependencyGenerator = VirtualDependencyGenerator[P_Project, P_VirtualDependency]
    P_VirtualDependencySummary = VirtualDependencySummary
    P_VirtualDependencyInstaller = VirtualDependencyInstaller[P_VirtualDependency, P_Report]
    P_VirtualDependencyScribe = VirtualDependencyScribe[P_VirtualDependency, P_Report]
    P_RenderedVirtualDependency = RenderedVirtualDependency[P_Report]
    P_VirtualDependencyHandler = VirtualDependencyHandler[P_Report]
