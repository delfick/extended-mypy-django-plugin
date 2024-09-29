import contextlib
import dataclasses
import importlib
import os
import pathlib
import sys
from collections.abc import Iterator, Sequence, Set

import configurations  # type: ignore[import-untyped]
from extended_mypy_django_plugin.django_analysis import Project, discovery, virtual_dependencies
from extended_mypy_django_plugin.django_analysis import protocols as d_protocols
from extended_mypy_django_plugin.plugin import VirtualDependencyHandlerBase


@dataclasses.dataclass(frozen=True, kw_only=True)
class ConfigurationsProject(Project):
    """
    Do necessary things to activate django-configurations before loading django
    """

    _cache: dict[str, type] = dataclasses.field(default_factory=dict)

    @property
    def Base(self) -> type:
        """
        This is the class that represents an instance of django.conf.settings

        We import it lazily so that it's used after the project has been loaded
        """
        key = "Base"
        if key not in self._cache:
            self._cache[key] = importlib.import_module("djangoexample.settings.base").Base
        return self._cache[key]

    @contextlib.contextmanager
    def setup_sys_path_and_env_vars(self) -> Iterator[None]:
        with super().setup_sys_path_and_env_vars():
            # Adjust Python path to ensure the tests package can be imported. This is required because
            # some third party libraries install a `tests` package into site-packages which prevents
            # mypy from being able to import the `tests.settings` module.
            package_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            sys.path.insert(0, package_root)

            configurations.setup()
            yield


@dataclasses.dataclass(frozen=True, kw_only=True)
class SettingsTypesDiscovery(discovery.NaiveSettingsTypesDiscovery[ConfigurationsProject]):
    def valid_setting_name(
        self, *, loaded_project: d_protocols.Loaded[ConfigurationsProject], name: str
    ) -> bool:
        if not super().valid_setting_name(loaded_project=loaded_project, name=name):
            return False

        # These are settings we give specific annotations for
        if name in ("CONFIGURATION", "DOTENV_LOADED", "SETTINGS_MODULE"):
            return True

        # If it has an annotation, it's valid and we can easily get that
        annotation = loaded_project.project.Base.__annotations__.get(name)
        if annotation:
            return True

        # Otherwise we only care about anything that is actually on Base
        # This must happen after looking at annotations so we find optional settings
        # that default to None!
        return getattr(loaded_project.project.Base, name, None) is not None

    def type_from_setting(
        self, loaded_project: d_protocols.Loaded[ConfigurationsProject], name: str, value: object
    ) -> str:
        if name == "CONFIGURATION":
            # This is a django-configurations setting
            return "str"

        if name == "DOTENV_LOADED":
            # This is a django-configurations setting
            return "bool"

        if name == "SETTINGS_MODULE":
            # This setting is also added
            return "str"

        annotation = loaded_project.project.Base.__annotations__.get(name)
        if annotation:
            return annotation

        found = getattr(loaded_project.project.Base, name)

        if isinstance(found, property) and found.fget:
            found = found.fget

        if isinstance(getattr(found, "__annotations__", None), dict) and (
            ret := found.__annotations__.get("return")
        ):
            return str(ret)

        return str(type(found))


class ConfigurationsReport(virtual_dependencies.Report):
    """
    Add to the additional deps files get such that anything that relies on django.conf.settings
    also relies on our djangoexample.settings.base module
    """

    def additional_deps(
        self,
        *,
        file_import_path: str,
        imports: Set[str],
        super_deps: Sequence[tuple[int, str, int]],
        django_settings_module: str,
        using_incremental_cache: bool,
    ) -> Sequence[tuple[int, str, int]]:
        """
        Find files that use django.conf.settings and make sure they are aware that
        changes to djangoexample.settings.base are relevant.
        """
        deps = list(
            super().additional_deps(
                file_import_path=file_import_path,
                imports=imports,
                super_deps=super_deps,
                django_settings_module=django_settings_module,
                using_incremental_cache=using_incremental_cache,
            )
        )

        if "django.conf.settings" in imports or any(
            mod == django_settings_module for _, mod, _ in deps
        ):
            # Statically we need to know if base.Base has different names/types
            # So that django.conf.settings is correct
            dep = (10, "djangoexample.settings.base", -1)
            if dep not in deps:
                deps.append(dep)

        return deps


class VirtualDependencyHandler(VirtualDependencyHandlerBase[ConfigurationsProject]):
    """
    Used by the mypy plugin to load django for two purposes:

    * Determine if dmypy needs to be restarted
    * Understand how to get concrete models/querysets given concrete annotations
    """

    @classmethod
    def make_project(
        cls, *, project_root: pathlib.Path, django_settings_module: str
    ) -> ConfigurationsProject:
        return ConfigurationsProject(
            root_dir=project_root,
            additional_sys_path=[str(project_root)],
            env_vars={
                "DJANGO_SETTINGS_MODULE": django_settings_module,
                "DJANGO_CONFIGURATION": "Dev",
            },
            discovery=discovery.Discovery(discover_settings_types=SettingsTypesDiscovery()),
        )

    def get_report_maker(self) -> d_protocols.ReportMaker[virtual_dependencies.Report]:
        return ConfigurationsReport
