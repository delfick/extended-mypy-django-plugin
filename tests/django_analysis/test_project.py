import inspect
import os
import pathlib
import sys
import textwrap
from typing import TYPE_CHECKING

import pytest

from extended_mypy_django_plugin.django_analysis import project, protocols

project_root = pathlib.Path(__file__).parent.parent.parent


def _hasher(*parts: bytes) -> str:
    return f"||hashed>>{' '.join(p.decode() for p in parts)}||"


if TYPE_CHECKING:
    _h: protocols.Hasher = _hasher


class TestReplacedEnvVarsAndSysPath:
    def test_it_can_handle_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("one", "one_val")
        monkeypatch.setenv("two", "two_val")

        monkeypatch.setenv("three", "tobedeleted")
        monkeypatch.delenv("three")

        all_env = dict(os.environ)

        assert "three" not in all_env
        assert all_env["one"] == "one_val"
        assert all_env["two"] == "two_val"

        with project.replaced_env_vars_and_sys_path(
            additional_sys_path=[], env_vars={"one": "blah", "three": "twenty"}
        ):
            changed = dict(os.environ)

        assert dict(os.environ) == all_env
        assert all_env != changed
        assert changed == {**all_env, "one": "blah", "three": "twenty"}

    def test_it_can_handle_changes_to_sys_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "path", ["one", "two", "three"])

        all_path = list(sys.path)
        assert all_path == ["one", "two", "three"]

        with project.replaced_env_vars_and_sys_path(
            additional_sys_path=["two", "four"], env_vars={}
        ):
            changed = list(sys.path)

        assert list(sys.path) == ["one", "two", "three"]
        assert changed == ["one", "two", "three", "four"]


class TestProject:
    def test_getting_an_analyzed_project(
        self, pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Using pytester to make it easier to run a test in a subprocess so we don't poison the import space
        """

        def test_getting_project() -> None:
            import dataclasses
            import os
            import pathlib
            from collections.abc import Set
            from typing import TYPE_CHECKING, cast

            from django.apps.registry import Apps
            from django.conf import LazySettings

            from extended_mypy_django_plugin.django_analysis import Project

            @dataclasses.dataclass(frozen=True, kw_only=True)
            class FakeModule:
                hasher: protocols.Hasher = _hasher
                virtual_dependency_import_path: protocols.ImportPath = dataclasses.field(
                    default_factory=lambda: protocols.ImportPath("virtual")
                )
                installed: bool = True
                import_path: protocols.ImportPath = dataclasses.field(
                    default_factory=lambda: protocols.ImportPath("somewhere")
                )
                defined_models_by_name: protocols.DefinedModelsMap = dataclasses.field(
                    default_factory=dict
                )
                related_modules: Set[protocols.Module] = dataclasses.field(default_factory=set)
                models_hash: str = ""

            fake_module: protocols.Module = FakeModule()

            class Discovery:
                def discover_settings_types(
                    self, loaded_project: protocols.LoadedProject, /
                ) -> protocols.SettingsTypesMap:
                    assert (
                        loaded_project.settings.UNIQUE_SETTING_TO_EXTENDED_MYPY_PLUGIN_DJANGOEXAMPLE  # type: ignore[misc]
                        == "unique"
                    )
                    return {"not": "accurate"}

                def discover_installed_models(
                    self, loaded_project: protocols.LoadedProject, /
                ) -> protocols.ModelModulesMap:
                    return {fake_module.import_path: fake_module}

            if TYPE_CHECKING:
                _sta: protocols.Discovery = cast(Discovery, None)

            root_dir = pathlib.Path(os.environ["PROJECT_ROOT"]) / "example"
            project = Project(
                root_dir=root_dir,
                hasher=_hasher,
                additional_sys_path=[str(root_dir)],
                discovery=Discovery(),
                env_vars={"DJANGO_SETTINGS_MODULE": "djangoexample.settings"},
            )

            with project.instantiate_django() as loaded_project:
                discovered_project = loaded_project.perform_discovery()

            assert loaded_project.root_dir == root_dir
            assert loaded_project.hasher is _hasher
            assert loaded_project.env_vars == project.env_vars
            assert isinstance(loaded_project.settings, LazySettings)
            assert (
                loaded_project.settings.UNIQUE_SETTING_TO_EXTENDED_MYPY_PLUGIN_DJANGOEXAMPLE  # type: ignore[misc]
                == "unique"
            )
            assert isinstance(loaded_project.apps, Apps)

            assert discovered_project.loaded_project is loaded_project
            assert discovered_project.installed_apps == [
                "django.contrib.admin",
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "django.contrib.sessions",
                "django.contrib.messages",
                "django.contrib.staticfiles",
                "djangoexample.exampleapp",
                "djangoexample.exampleapp2",
                "djangoexample.only_abstract",
                "djangoexample.no_models",
                "djangoexample.relations1",
                "djangoexample.relations2",
            ]
            assert discovered_project.settings_types == {"not": "accurate"}
            assert discovered_project.installed_models_modules == {
                fake_module.import_path: fake_module
            }

        test_content = (
            "from extended_mypy_django_plugin.django_analysis import protocols"
            + "\n\n"
            + inspect.getsource(_hasher)
            + "\n\n"
            + textwrap.dedent(inspect.getsource(test_getting_project))
        )
        pytester.makepyfile(test_content)

        monkeypatch.setenv("PROJECT_ROOT", str(project_root))
        result = pytester.runpytest_subprocess("-vvv")
        result.assert_outcomes(passed=1)
