import inspect
import os
import pathlib
import sys
import textwrap
from collections.abc import Sequence
from typing import TYPE_CHECKING

import pytest

from extended_mypy_django_plugin.django_analysis import ImportPath, project, protocols

project_root = pathlib.Path(__file__).parent.parent.parent


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
    def test_getting_an_discovered_project(
        self, pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Using pytester to make it easier to run a test in a subprocess so we don't poison the import space
        """

        def test_getting_project() -> None:
            import dataclasses
            import os
            import pathlib
            from typing import cast

            from django.apps.registry import Apps
            from django.conf import LazySettings

            from extended_mypy_django_plugin.django_analysis import Project

            @dataclasses.dataclass(frozen=True, kw_only=True)
            class FakeModel:
                model_name: str = "MyModel"
                module_import_path: protocols.ImportPath = dataclasses.field(
                    default_factory=lambda: ImportPath("fake.model")
                )
                import_path: protocols.ImportPath = dataclasses.field(
                    default_factory=lambda: ImportPath("fake.model.MyModel")
                )
                is_abstract: bool = False
                default_custom_queryset: protocols.ImportPath | None = None
                all_fields: protocols.FieldsMap = dataclasses.field(default_factory=dict)
                models_in_mro: Sequence[protocols.ImportPath] = dataclasses.field(
                    default_factory=list
                )

            @dataclasses.dataclass(frozen=True, kw_only=True)
            class FakeModule:
                installed: bool = True
                import_path: protocols.ImportPath = dataclasses.field(
                    default_factory=lambda: ImportPath("somewhere")
                )
                defined_models: protocols.ModelMap = dataclasses.field(
                    default_factory=lambda: {fake_model.import_path: fake_model}
                )
                models_hash: str = ""

            fake_model: protocols.Model = FakeModel()
            fake_module: protocols.Module = FakeModule()

            class Discovery:
                def discover_settings_types(
                    self, loaded_project: protocols.Loaded[Project], /
                ) -> protocols.SettingsTypesMap:
                    assert (
                        loaded_project.settings.UNIQUE_SETTING_TO_EXTENDED_MYPY_PLUGIN_DJANGOEXAMPLE  # type: ignore[misc]
                        == "unique"
                    )
                    return {"not": "accurate"}

                def discover_installed_models(
                    self, loaded_project: protocols.Loaded[Project], /
                ) -> protocols.ModelModulesMap:
                    return {fake_module.import_path: fake_module}

                def discover_concrete_models(
                    self, loaded_project: protocols.Loaded[Project], models: protocols.ModelMap, /
                ) -> protocols.ConcreteModelsMap:
                    assert models == {fake_model.import_path: fake_model}
                    return {fake_model.import_path: [fake_model]}

            if TYPE_CHECKING:
                _sta: protocols.Discovery[Project] = cast(Discovery, None)

            root_dir = pathlib.Path(os.environ["PROJECT_ROOT"]) / "example"
            project = Project(
                root_dir=root_dir,
                additional_sys_path=[str(root_dir)],
                discovery=Discovery(),
                env_vars={"DJANGO_SETTINGS_MODULE": "djangoexample.settings"},
            )

            loaded_project = project.load_project()
            discovered_project = loaded_project.perform_discovery()

            assert loaded_project.root_dir == root_dir
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
                "djangoexample.empty_models",
            ]
            assert discovered_project.settings_types == {"not": "accurate"}
            assert discovered_project.installed_models_modules == {
                fake_module.import_path: fake_module
            }
            assert discovered_project.all_models == {fake_model.import_path: fake_model}
            assert discovered_project.concrete_models == {fake_model.import_path: [fake_model]}

        test_content = (
            "from extended_mypy_django_plugin.django_analysis import protocols, ImportPath"
            + "\n"
            + "from typing import TYPE_CHECKING"
            + "\n"
            + "from collections.abc import Sequence"
            + "\n\n"
            + textwrap.dedent(inspect.getsource(test_getting_project))
        )
        pytester.makepyfile(test_content)

        monkeypatch.setenv("PROJECT_ROOT", str(project_root))
        result = pytester.runpytest_subprocess("-vvv")
        result.assert_outcomes(passed=1)
