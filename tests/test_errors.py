import dataclasses
import pathlib
import re
import sys
import textwrap

import pytest
from extended_mypy_django_plugin_test_driver import (
    Scenario,
    ScenarioBuilder,
    ScenarioRunner,
    assertions,
)
from pytest_typing_runner import expectations, protocols, runners


@dataclasses.dataclass(frozen=True, kw_only=True)
class SimpleExpectation:
    options: protocols.RunOptions[Scenario]

    @dataclasses.dataclass(frozen=True, kw_only=True)
    class Expectation:
        result: protocols.RunResult
        notice_checker: protocols.NoticeChecker[Scenario]

        def check(self) -> None:
            raise NotImplementedError()

    expectation: type[Expectation]

    @classmethod
    def setup(cls, expectation: type[Expectation], /) -> protocols.ExpectationsSetup[Scenario]:
        def make(
            *, options: protocols.RunOptions[Scenario]
        ) -> protocols.ExpectationsMaker[Scenario]:
            return cls(expectation=expectation, options=options)

        return make

    def __call__(self) -> protocols.Expectations[Scenario]:
        Expectation = self.expectation

        class Expected:
            def check(self, *, notice_checker: protocols.NoticeChecker[Scenario]) -> None:
                Expectation(notice_checker=notice_checker, result=notice_checker.result).check()

        return Expected()


class TestErrors:
    def test_it_complains_if_annotating_a_typevar(self, builder: ScenarioBuilder) -> None:
        @builder.run_and_check_after
        def _() -> None:
            builder.set_installed_apps("example")
            builder.on("example/__init__.py").set("")

            builder.on("example/apps.py").set(
                """
                from django.apps import AppConfig

                class Config(AppConfig):
                    name = "example"
                """,
            )

            builder.on("example/models.py").set(
                """
                from __future__ import annotations

                from django.db import models
                from typing import TypeVar
                from typing_extensions import Self
                from extended_mypy_django_plugin import Concrete, DefaultQuerySet

                T_Leader = TypeVar("T_Leader", bound="Concrete[Leader]")

                class Leader(models.Model):
                    @classmethod
                    def new(cls) -> Concrete[Self]:
                        # ^ ERROR(misc) ^ Using a concrete annotation on a TypeVar is not currently supported
                        raise NotImplementedError()

                    class Meta:
                        abstract = True

                class Follower1(Leader):
                    pass

                def make_leader(model: type[T_Leader]) -> Concrete[T_Leader]:
                    # ^ ERROR(misc) ^ Using a concrete annotation on a TypeVar is not currently supported
                    raise NotImplementedError()

                def make_qs(model: type[T_Leader]) -> DefaultQuerySet[T_Leader]:
                    # ^ ERROR(misc) ^ Using a concrete annotation on a TypeVar is not currently supported
                    raise NotImplementedError()
                """,
            )

    def test_gracefully_handles_determine_version_failure_on_startup(
        self,
        scenario: Scenario,
        scenario_runner: ScenarioRunner,
        tmp_path: pathlib.Path,
    ) -> None:
        options = runners.RunOptions.create(scenario_runner)
        if not options.program_runner_maker.is_daemon:
            pytest.skip("Test only relevant for the daemon")

        plugin_provider = tmp_path / "plugin.py"

        plugin_provider.write_text(
            textwrap.dedent("""
            import pathlib

            from extended_mypy_django_plugin.django_analysis import Project
            from extended_mypy_django_plugin.plugin import PluginProvider, VirtualDependencyHandler, ExtendedMypyStubs


            class VirtualDependencyHandler(VirtualDependencyHandler):
                @classmethod
                def make_project(
                    cls, *, project_root: pathlib.Path, django_settings_module: str
                ) -> Project:
                    raise ValueError("Computer says no")


            plugin = PluginProvider(ExtendedMypyStubs, VirtualDependencyHandler.create_report, locals())
            """)
        )

        scenario.info.mypy_configuration_content = textwrap.dedent(
            f"""
            [mypy]
            plugins = {plugin_provider}
            mypy_path = $MYPY_CONFIG_FILE_DIR/.mypy_django_scratch/test

            [mypy.plugins.django-stubs]
            django_settings_module = mysettings
            scratch_path = $MYPY_CONFIG_FILE_DIR/.mypy_django_scratch/test
            """
        )

        @dataclasses.dataclass(frozen=True, kw_only=True)
        class CheckFails(SimpleExpectation.Expectation):
            def check(self) -> None:
                assert self.result.exit_code != 0

                assertions.assert_glob_lines(
                    self.result.stdout + self.result.stderr,
                    f"""
                Error constructing plugin instance of Plugin
                
                Daemon crashed!
                Traceback (most recent call last):
                File "*extended_mypy_django_plugin/_plugin/plugin.py", line *, in make_virtual_dependency_report
                File "{plugin_provider}", line *, in make_project
                ValueError: Computer says no
                """,
                )

        scenario_runner.run_and_check(
            setup_expectations=SimpleExpectation.setup(CheckFails), options=options
        )

    def test_gracefully_handles_determine_version_failure_on_subsequent_run(
        self, scenario: Scenario, scenario_runner: ScenarioRunner, tmp_path: pathlib.Path
    ) -> None:
        options = runners.RunOptions.create(scenario_runner)
        if not options.program_runner_maker.is_daemon:
            pytest.skip("Test only relevant for the daemon")

        plugin_provider = tmp_path / "plugin.py"
        marker = tmp_path / "marker"
        marker2 = tmp_path / "marker2"

        # pytest plugin I use needs work which is under way but in the meantime I must hack around
        # how inside the test I can't turn off the auto second try
        marker.write_text("")
        marker2.write_text("")

        # Changing the contents of this file will trigger the daemon to restart
        # So we instead rely on the existence or absence of a file to trigger the error
        plugin_provider.write_text(
            textwrap.dedent(f"""
            import pathlib

            from extended_mypy_django_plugin.django_analysis import Project
            from extended_mypy_django_plugin import main


            class VirtualDependencyHandler(main.VirtualDependencyHandler):
                @classmethod
                def make_project(
                    cls, *, project_root: pathlib.Path, django_settings_module: str
                ) -> Project:
                    if pathlib.Path("{marker}").exists():
                        pathlib.Path("{marker}").unlink()
                        return super().make_project(
                            project_root=project_root,
                            django_settings_module=django_settings_module,
                        )

                    if pathlib.Path("{marker2}").exists():
                        pathlib.Path("{marker2}").unlink()
                        return super().make_project(
                            project_root=project_root,
                            django_settings_module=django_settings_module,
                        )

                    # Make this only fail on the startup to show if the run after restart works then
                    # then this failing doesn't break the daemon
                    pathlib.Path("{marker}").write_text('')
                    raise ValueError("Computer says no")


            plugin = main.PluginProvider(main.ExtendedMypyStubs, VirtualDependencyHandler.create_report, locals())
        """)
        )

        scenario.info.mypy_configuration_content = textwrap.dedent(
            f"""
            [mypy]
            plugins = {plugin_provider}
            mypy_path = $MYPY_CONFIG_FILE_DIR/.mypy_django_scratch/test

            [mypy.plugins.django-stubs]
            django_settings_module = mysettings
            scratch_path = $MYPY_CONFIG_FILE_DIR/.mypy_django_scratch/test
            """
        )

        scenario_runner.run_and_check(
            setup_expectations=expectations.Expectations.setup_for_success, options=options
        )

        called: list[int] = []

        @dataclasses.dataclass(frozen=True, kw_only=True)
        class CheckNoCrashShowsFailure(SimpleExpectation.Expectation):
            def check(self) -> None:
                called.append(self.result.exit_code)

                assert self.result.exit_code == 0
                command = (
                    f"{sys.executable} -m extended_mypy_django_plugin.scripts.determine_django_state"
                    f" --config-file mypy.ini"
                    f" --mypy-plugin {plugin_provider}"
                    " --version-file *"
                )

                assertions.assert_glob_lines(
                    self.result.stdout + self.result.stderr,
                    f"""
                    Failed to determine information about the django setup

                    > {command}
                    |
                    | Traceback (most recent call last):
                    |   File "{plugin_provider}", line *, in make_project
                    |     raise ValueError("Computer says no")
                    | ValueError: Computer says no
                    |
                    """,
                )

        scenario_runner.run_and_check(
            setup_expectations=SimpleExpectation.setup(CheckNoCrashShowsFailure), options=options
        )
        assert called == [0]

        @dataclasses.dataclass(frozen=True, kw_only=True)
        class CheckNoOutput(SimpleExpectation.Expectation):
            def check(self) -> None:
                called.append(self.result.exit_code)

                assert self.result.exit_code == 0
                assert re.match(
                    r"Success: no issues found in \d+ source files?",
                    (self.result.stdout + self.result.stderr).strip(),
                )

        marker.write_text("")
        scenario_runner.run_and_check(
            setup_expectations=SimpleExpectation.setup(CheckNoOutput), options=options
        )
        assert called == [0, 0]

    def test_knowing_types_of_fields_on_parent_classes(
        self, scenario: Scenario, builder: ScenarioBuilder
    ) -> None:
        """
        This is a regression test to ensure that get_additional_deps doesn't cause class
        definitions to not understand parent types
        """

        @builder.run_and_check_after
        def _() -> None:
            builder.set_installed_apps("example", "example2")
            for app in ("example", "example2"):
                builder.on(f"{app}/__init__.py").set("")
                builder.on(f"{app}/apps.py").set(
                    f"""
                    from django.apps import AppConfig

                    class Config(AppConfig):
                        name = "{app}"
                    """,
                )

            builder.on("example/models/__init__.py").set(
                """
                from .parent import Parent 
                """
            )
            builder.on("example2/models/__init__.py").set(
                """
                from .children import Child
                """
            )

            builder.on("example/models/parent.py").set(
                """
                from django.db import models

                class Parent(models.Model):
                    response_body = models.TextField(max_length=12, blank=True)

                    class Meta:
                        abstract = True
                """,
            )

            builder.on("example2/models/children.py").set(
                """
                from example import models as common_models
                from typing import TYPE_CHECKING
                from django.db import models

                class Child(common_models.Parent):
                    response_body = models.BooleanField()
                    # ^ ERROR(assignment) ^ Incompatible types in assignment (expression has type "bool", base class "Parent" defined the type as "str")
                """,
            )
