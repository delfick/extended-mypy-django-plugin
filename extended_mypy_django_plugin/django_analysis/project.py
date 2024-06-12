from __future__ import annotations

import contextlib
import dataclasses
import os
import pathlib
import sys
import types
from collections.abc import Iterator, Mapping, Sequence
from typing import TYPE_CHECKING, cast

from django.apps.registry import Apps
from django.conf import LazySettings

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
    hasher: protocols.Hasher

    analyzers: protocols.Analyzers

    @contextlib.contextmanager
    def setup_sys_path_and_env_vars(self) -> Iterator[None]:
        with replaced_env_vars_and_sys_path(
            additional_sys_path=self.additional_sys_path, env_vars=self.env_vars
        ):
            yield

    @contextlib.contextmanager
    def instantiate_django(self) -> Iterator[protocols.LoadedProject]:
        with self.setup_sys_path_and_env_vars():
            from django.apps import apps
            from django.conf import settings

            if not settings.configured:
                settings._setup()  # type: ignore[misc]
            apps.populate(settings.INSTALLED_APPS)

            assert apps.apps_ready, "Apps are not ready"
            assert settings.configured, "Settings are not configured"

            yield LoadedProject(
                root_dir=self.root_dir,
                hasher=self.hasher,
                env_vars=self.env_vars,
                settings=settings,
                apps=apps,
                analyzers=self.analyzers,
            )


@dataclasses.dataclass(frozen=True, kw_only=True)
class LoadedProject:
    root_dir: pathlib.Path
    env_vars: Mapping[str, str]
    settings: LazySettings
    apps: Apps
    hasher: protocols.Hasher

    analyzers: protocols.Analyzers

    def analyze_project(self) -> protocols.AnalyzedProject:
        return AnalyzedProject(
            hasher=self.hasher,
            loaded_project=self,
            installed_apps=self.settings.INSTALLED_APPS,
            settings_types=self.analyzers.analyze_settings_types(self),
            known_model_modules=self.analyzers.analyze_known_models(self),
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class AnalyzedProject:
    hasher: protocols.Hasher
    loaded_project: LoadedProject

    installed_apps: list[str]
    settings_types: protocols.SettingsTypesMap
    known_model_modules: protocols.ModelModulesMap


if TYPE_CHECKING:
    _P: protocols.Project = cast(Project, None)
    _LP: protocols.LoadedProject = cast(LoadedProject, None)
    _AP: protocols.AnalyzedProject = cast(AnalyzedProject, None)
