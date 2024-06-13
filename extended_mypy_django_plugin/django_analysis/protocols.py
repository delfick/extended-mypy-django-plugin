from __future__ import annotations

import contextlib
import pathlib
from collections.abc import Hashable, Iterator, Mapping, Sequence
from typing import TYPE_CHECKING, Any, NewType, Protocol, Union

from django.apps.registry import Apps
from django.conf import LazySettings
from django.db import models

if TYPE_CHECKING:
    from django.contrib.contenttypes.fields import GenericForeignKey
    from django.db.models.fields.related import ForeignObjectRel

ImportPath = NewType("ImportPath", str)
FieldsMap = Mapping[str, "Field"]
ModelModulesMap = Mapping[ImportPath, "Module"]
DefinedModelsMap = Mapping[str, "Model"]
SettingsTypesMap = Mapping[str, str]
DjangoField = Union["models.fields.Field[Any, Any]", "ForeignObjectRel", "GenericForeignKey"]


class Hasher(Protocol):
    def __call__(self, *parts: bytes) -> str:
        """
        Given some strings, create a single hash of all that data
        """


class SettingsTypesAnalyzer(Protocol):
    """
    Used determine the Django settings and their types in a Django project
    """

    def __call__(self, loaded_project: LoadedProject, /) -> SettingsTypesMap: ...


class KnownModelsAnalayzer(Protocol):
    """
    Used Find and analyze the known models in a Django project
    """

    def __call__(self, loaded_project: LoadedProject, /) -> ModelModulesMap: ...


class Analyzers(Protocol):
    """
    A container for all the different analyzers
    """

    @property
    def analyze_settings_types(self) -> SettingsTypesAnalyzer:
        """
        Used to analyze the settings types in a django project
        """

    @property
    def analyze_known_models(self) -> KnownModelsAnalayzer:
        """
        Used to analyze the django orm models in a Django project
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

    @property
    def hasher(self) -> Hasher:
        """
        An object for creating hashes from strings
        """

    @contextlib.contextmanager
    def setup_sys_path_and_env_vars(self) -> Iterator[None]:
        """
        Do necessary work to setup and cleanup changes to sys.path and os.environ to prepare
        for a django instantiation.
        """

    @contextlib.contextmanager
    def instantiate_django(self) -> Iterator[LoadedProject]:
        """
        Do necessary work to load Django into memory

        It is expected that an implementation will use self.setup_sys_path_and_env_vars to
        setup and cleanup required changes to sys.path and os.environ
        """


class LoadedProject(Protocol):
    """
    Represents a Django project that has been setup and loaded into memory
    """

    @property
    def root_dir(self) -> pathlib.Path:
        """
        Where the django project lives
        """

    @property
    def hasher(self) -> Hasher:
        """
        An object for creating hashes from strings
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

    def analyze_project(self) -> AnalyzedProject:
        """
        Perform analysis on the loaded django project
        """


class AnalyzedProject(Protocol):
    @property
    def loaded_project(self) -> LoadedProject:
        """
        The loaded django project that was analyzed
        """

    @property
    def hasher(self) -> Hasher:
        """
        An object for creating hashes from strings
        """

    @property
    def known_model_modules(self) -> ModelModulesMap:
        """
        The known modules that contain installed Django Models
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
    def defined_models_by_name(self) -> DefinedModelsMap:
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
    def hasher(self) -> Hasher:
        """
        An object for creating hashes from strings
        """

    @property
    def namespace(self) -> str:
        """
        The import namespace for virtual dependencies
        """

    def __call__(self, module: ImportPath, /) -> ImportPath:
        """
        Return a deterministically determined name representing this module import path
        """


class VirtualDependencyCreator(Protocol):
    """
    Represents the work to create virtual dependencies for a django project
    """

    @property
    def analyzed_project(self) -> AnalyzedProject:
        """
        The analyzed project dependencies are being made for
        """

    @property
    def virtual_dependency_root(self) -> pathlib.Path:
        """
        The path to put the virtual dependency folder into
        """

    def generate_virtual_dependencies(self, tmp_path: pathlib.Path) -> None:
        """
        Generate all the virtual dependencies onto disk for a project into the provided path
        """

    def replace_reports(self, tmp_path: pathlib.Path) -> None:
        """
        Replace the virtual dependencies with those found in the tmp_path, making sure to delete
        left over reports that represent deleted modules
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
    def deps_hash(self) -> str | None:
        """
        The hash of the related modules/models if this module is part of the installed apps
        """


class VirtualDependency(Protocol):
    """
    Represents the information held by a virtual dependency for a module
    """

    @property
    def hasher(self) -> Hasher:
        """
        An object for creating hashes from strings
        """

    @property
    def module(self) -> Module:
        """
        The module represented by this virtual dependency
        """

    @property
    def interface_differentiator(self) -> str:
        """
        A string used to change the public interface of this virtual dependency
        """

    @property
    def summary(self) -> VirtualDependencySummary:
        """
        The parts that make up a final hash for this virtual dependency
        """

    @property
    def concrete_annotations(self) -> Mapping[Model, Sequence[Model]]:
        """
        The models known by this module and their concrete children
        """


if TYPE_CHECKING:
    P_Model = Model
    P_Field = Field
    P_Module = Module
    P_Hasher = Hasher
    P_Project = Project
    P_Analyzers = Analyzers
    P_LoadedProject = LoadedProject
    P_AnalyzedProject = AnalyzedProject
    P_VirtualDependency = VirtualDependency
    P_KnownModelsAnalayzer = KnownModelsAnalayzer
    P_SettingsTypesAnalyzer = SettingsTypesAnalyzer
    P_VirtualDependencyNamer = VirtualDependencyNamer
    P_VirtualDependencySummary = VirtualDependencySummary
    P_VirtualDependencyCreator = VirtualDependencyCreator
