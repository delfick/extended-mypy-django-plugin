from __future__ import annotations

import contextlib
import dataclasses
import os
import pathlib
import sys
import types
from collections.abc import Iterator, Mapping, Sequence
from typing import TYPE_CHECKING, Generic, cast

from django.apps.registry import Apps
from django.conf import LazySettings
from typing_extensions import Self

from . import protocols


@dataclasses.dataclass(frozen=True, kw_only=True)
class replaced_env_vars_and_sys_path:
    """
    Helper to modify sys.path and os.environ such that those changes are reversed
    upon exiting the contextmanager
    """

    additional_sys_path: Sequence[str]
    env_vars: Mapping[str, str]

    undo_env: dict[str, str | None] = dataclasses.field(init=False, default_factory=dict)
    remove_path: list[str] = dataclasses.field(init=False, default_factory=list)

    def __enter__(self) -> None:
        # Determine what to undo later
        for k, v in self.env_vars.items():
            if k not in os.environ:
                self.undo_env[k] = None
            else:
                self.undo_env[k] = os.environ[k]

        for path in self.additional_sys_path:
            if path not in sys.path:
                self.remove_path.append(path)

        # Make the change itself
        for path in self.additional_sys_path:
            if path not in sys.path:
                sys.path.append(path)

        for k, v in self.env_vars.items():
            os.environ[k] = v

    def __exit__(self, exc_type: type[Exception], tb: types.TracebackType, exc: Exception) -> None:
        for path in self.remove_path:
            if path in sys.path:
                sys.path.remove(path)

        for k, v in self.undo_env.items():
            if v is None:
                if k in os.environ:
                    del os.environ[k]
            else:
                os.environ[k] = v


@dataclasses.dataclass(frozen=True, kw_only=True)
class Project:
    root_dir: pathlib.Path
    additional_sys_path: Sequence[str]
    env_vars: Mapping[str, str]

    discovery: protocols.Discovery[Self]

    @contextlib.contextmanager
    def setup_sys_path_and_env_vars(self) -> Iterator[None]:
        with replaced_env_vars_and_sys_path(
            additional_sys_path=self.additional_sys_path, env_vars=self.env_vars
        ):
            yield

    @contextlib.contextmanager
    def instantiate_django(self) -> Iterator[protocols.Loaded[Self]]:
        with self.setup_sys_path_and_env_vars():
            from django.apps import apps
            from django.conf import settings

            if not settings.configured:
                settings._setup()  # type: ignore[misc]
            apps.populate(settings.INSTALLED_APPS)

            assert apps.apps_ready, "Apps are not ready"
            assert settings.configured, "Settings are not configured"

            yield Loaded(
                project=self,
                root_dir=self.root_dir,
                env_vars=self.env_vars,
                settings=settings,
                apps=apps,
                discovery=self.discovery,
            )

    def load_project(self) -> protocols.Loaded[Self]:
        with self.instantiate_django() as loaded_project:
            return loaded_project


@dataclasses.dataclass(frozen=True, kw_only=True)
class Loaded(Generic[protocols.T_Project]):
    project: protocols.T_Project
    root_dir: pathlib.Path
    env_vars: Mapping[str, str]
    settings: LazySettings
    apps: Apps

    discovery: protocols.Discovery[protocols.T_Project]

    def perform_discovery(self) -> protocols.Discovered[protocols.T_Project]:
        installed_models_modules = self.discovery.discover_installed_models(self)

        all_models: dict[protocols.ImportPath, protocols.Model] = {}
        for module in installed_models_modules.values():
            all_models.update(module.defined_models)

        return Discovered(
            loaded_project=self,
            all_models=all_models,
            installed_apps=self.settings.INSTALLED_APPS,
            settings_types=self.discovery.discover_settings_types(self),
            installed_models_modules=installed_models_modules,
            concrete_models=self.discovery.discover_concrete_models(self, all_models),
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Discovered(Generic[protocols.T_Project]):
    loaded_project: Loaded[protocols.T_Project]

    all_models: protocols.ModelMap
    installed_apps: list[str]
    settings_types: protocols.SettingsTypesMap
    concrete_models: protocols.ConcreteModelsMap
    installed_models_modules: protocols.ModelModulesMap


if TYPE_CHECKING:
    _P: protocols.Project = cast(Project, None)
    _LP: protocols.P_Loaded = cast(Loaded[protocols.P_Project], None)
    _AP: protocols.P_Discovered = cast(Discovered[protocols.P_Project], None)

    C_Project = Project
    _CLP: protocols.Loaded[C_Project] = cast(Loaded[C_Project], None)
    _CAP: protocols.Discovered[C_Project] = cast(Discovered[C_Project], None)
