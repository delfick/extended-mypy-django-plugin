import pathlib
import sys
import textwrap

import pytest
import pytest_mypy_plugins.utils
from extended_mypy_django_plugin_test_driver import OutputBuilder, Scenario, assertions
from pytest_mypy_plugins import OutputChecker


class TestErrors:
    def test_cant_use_typevar_concrete_annotation_in_function_or_method_typeguard(
        self, scenario: Scenario
    ) -> None:
        @scenario.run_and_check_mypy_after
        def _(expected: OutputBuilder) -> None:
            scenario.file(
                expected,
                "main.py",
                """
                from typing import TypeGuard, TypeVar, cast, TypeVar

                from myapp.models import Child1, Parent

                from extended_mypy_django_plugin import Concrete

                T_Parent = TypeVar("T_Parent", bound=Parent)

                def function_with_type_typeguard(
                    cls: type[T_Parent]
                ) -> TypeGuard[type[Concrete[T_Parent]]]:
                    return hasattr(cls, "objects")

                cls1: type[Parent] = Child1
                assert function_with_type_typeguard(cls1)
                # ^ ERROR(misc) ^ Can't use a TypeGuard that uses a Concrete Annotation that uses type variables
                cls1
                # ^ REVEAL ^ type[extended_mypy_django_plugin.annotations.Concrete[myapp.models.Parent]]

                def function_with_instance_typeguard(
                    instance: T_Parent
                ) -> TypeGuard[Concrete[T_Parent]]:
                    return True

                instance1: Parent = cast(Child1, None)
                assert function_with_instance_typeguard(instance1)
                # ^ ERROR(misc) ^ Can't use a TypeGuard that uses a Concrete Annotation that uses type variables
                instance1
                # ^ REVEAL ^ extended_mypy_django_plugin.annotations.Concrete[myapp.models.Parent]

                class Logic:
                    def method_with_type_typeguard(
                        self, cls: type[T_Parent]
                    ) -> TypeGuard[type[Concrete[T_Parent]]]:
                        return hasattr(cls, "objects")

                    def method_with_instance_typeguard(
                        self, instance: T_Parent
                    ) -> TypeGuard[Concrete[T_Parent]]:
                        return True

                logic = Logic()
                cls2: type[Parent] = Child1
                assert logic.method_with_type_typeguard(cls2)
                # ^ ERROR(misc) ^ Can't use a TypeGuard that uses a Concrete Annotation that uses type variables
                cls2
                # ^ REVEAL ^ type[extended_mypy_django_plugin.annotations.Concrete[T_Parent`-1]]

                instance2: Parent = cast(Child1, None)
                assert logic.method_with_instance_typeguard(instance2)
                # ^ ERROR(misc) ^ Can't use a TypeGuard that uses a Concrete Annotation that uses type variables
                instance2
                # ^ REVEAL ^ extended_mypy_django_plugin.annotations.Concrete[T_Parent`-1]
                """,
            )

    def test_gracefully_handles_determine_version_failure_on_startup(
        self, scenario: Scenario, tmp_path: pathlib.Path
    ) -> None:
        if not scenario.for_daemon:
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

        scenario.scenario.additional_mypy_config = textwrap.dedent(
            f"""
            [mypy]
            plugins = {plugin_provider}

            [mypy.plugins.django-stubs]
            django_settings_module = mysettings
            """
        )

        with pytest.raises(pytest_mypy_plugins.utils.TypecheckAssertionError) as err:

            @scenario.run_and_check_mypy_after
            def _(expected: OutputBuilder) -> None:
                pass

        assert err.value.mypy_output is not None

        assertions.assert_glob_lines(
            err.value.mypy_output,
            f"""
            Error constructing plugin instance of Plugin
            
            Daemon crashed!
            Traceback (most recent call last):
            File "*extended_mypy_django_plugin/_plugin/plugin.py", line *, in make_virtual_dependency_report
            File "{plugin_provider}", line *, in make_project
            ValueError: Computer says no
            """,
        )

    def test_gracefully_handles_determine_version_failure_on_subsequent_run(
        self, scenario: Scenario, tmp_path: pathlib.Path
    ) -> None:
        if not scenario.for_daemon:
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
            from extended_mypy_django_plugin.main import PluginProvider, VirtualDependencyHandler, ExtendedMypyStubs


            class VirtualDependencyHandler(VirtualDependencyHandler):
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


            plugin = PluginProvider(ExtendedMypyStubs, VirtualDependencyHandler.create_report, locals())
        """)
        )

        scenario.scenario.additional_mypy_config = textwrap.dedent(
            f"""
            [mypy]
            plugins = {plugin_provider}

            [mypy.plugins.django-stubs]
            django_settings_module = mysettings
            """
        )

        @scenario.run_and_check_mypy_after
        def _(expected: OutputBuilder) -> None:
            pass

        called: list[int] = []

        class CheckNoCrashShowsFailure(OutputChecker):
            def check(self, ret_code: int, stdout: str, stderr: str) -> None:
                called.append(ret_code)

                assert ret_code == 0
                command = (
                    f"{sys.executable} -m extended_mypy_django_plugin.scripts.determine_django_state"
                    f" --config-file {scenario.scenario.execution_path}/mypy.ini"
                    f" --mypy-plugin {plugin_provider}"
                    " --version-file *"
                )

                assertions.assert_glob_lines(
                    stdout + stderr,
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

        scenario.run_and_check_mypy(scenario.expected, OutputCheckerKls=CheckNoCrashShowsFailure)
        assert called == [0]

        class CheckNoOutput(OutputChecker):
            def check(self, ret_code: int, stdout: str, stderr: str) -> None:
                called.append(ret_code)

                assert ret_code == 0
                assert stdout + stderr == ""

        marker.write_text("")
        scenario.run_and_check_mypy(scenario.expected, OutputCheckerKls=CheckNoOutput)
        assert called == [0, 0]
