from __future__ import annotations

import contextlib
import pathlib
from collections.abc import Hashable, Iterator, Mapping, Sequence
from typing import TYPE_CHECKING, Any, NewType, Protocol, TypeVar, Union

from django.apps.registry import Apps
from django.conf import LazySettings
from django.db import models
from typing_extensions import Self

if TYPE_CHECKING:
    from django.contrib.contenttypes.fields import GenericForeignKey
    from django.db.models.fields.related import ForeignObjectRel

T_Project = TypeVar("T_Project", bound="P_Project")
T_CO_VirtualDependency = TypeVar(
    "T_CO_VirtualDependency", bound="P_VirtualDependency", covariant=True
)

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

    @contextlib.contextmanager
    def instantiate_django(self) -> Iterator[Loaded[Self]]:
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
    def installed(self) -> bool:
        """
        Whether this module is part of the installed django apps
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


class VirtualDependencyFolder(Protocol[T_Project, T_CO_VirtualDependency]):
    """
    Object that manages the folder containing the on disk virtual dependencies
    """

    @property
    def discovered_project(self) -> Discovered[T_Project]:
        """
        The project with discovered information
        """

    @property
    def virtual_dependency_maker(
        self,
    ) -> VirtualDependencyMaker[T_Project, T_CO_VirtualDependency]:
        """
        Used to generate a virtual dependency for a module
        """

    def generate(self) -> GeneratedVirtualDependencies[T_CO_VirtualDependency]:
        """
        Generate the virtual dependencies for this project
        """


class GeneratedVirtualDependencies(Protocol[T_CO_VirtualDependency]):
    @property
    def virtual_dependencies(self) -> VirtualDependencyMap[T_CO_VirtualDependency]:
        """
        The virtual dependency items
        """

    def install(
        self, *, scratch_root: pathlib.Path, destination: pathlib.Path, hasher: Hasher
    ) -> None:
        """
        Install the virtual dependencies into their destination.

        Implementations should:

        * Build the reports in the scratch root before installing in the final destination
        * Clear out reports in the final destination that represent modules that don't exist anymore
        """


class VirtualDependencySummary(Protocol):
    """
    Represents the different hashes that make up a full hash for a virtual dependency

    This is used to determine if the dependency has changed or not
    """

    @property
    def virtual_dependency_name(self) -> ImportPath:
        """
        The import path the virtual dependency lives at
        """

    @property
    def module_import_path(self) -> ImportPath:
        """
        The import path to the real module this virtual dependency represents
        """

    @property
    def installed_apps_hash(self) -> str | None:
        """
        The hash of the installed apps if this module is part of the installed apps
        """

    @property
    def significant_info(self) -> Sequence[str] | None:
        """
        Strings representing significant information related to the module

        The idea is that changes in this list should warrant reloading Django in a fresh environment.

        This should be None if the module is not part of the installed apps.
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
    def interface_differentiator(self) -> str | None:
        """
        A string used to change the public interface of this virtual dependency

        Should be None when the module isn't installed
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

    P_VirtualDependency = VirtualDependency
    P_VirtualDependencyMaker = VirtualDependencyMaker[P_Project, P_VirtualDependency]
    P_VirtualDependencyNamer = VirtualDependencyNamer
    P_VirtualDependencyFolder = VirtualDependencyFolder[P_Project, P_VirtualDependency]
    P_VirtualDependencySummary = VirtualDependencySummary
    P_GeneratedVirtualDependencies = GeneratedVirtualDependencies[P_VirtualDependency]
