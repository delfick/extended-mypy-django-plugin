import os
import pathlib
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

        determine_script = tmp_path / "determine.py"

        determine_script.write_text(
            textwrap.dedent("""
        #!/usr/bin/env python

        from extended_mypy_django_plugin.scripts.determine_django_state import main


        if __name__ == "__main__":
            raise ValueError("Computer says no")
            main()
        """)
        )

        os.chmod(determine_script, 0o755)
        scenario.scenario.additional_mypy_config += (
            f"\ndetermine_django_state_script = {determine_script}"
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
            RuntimeError:
            Failed to determine information about the django setup
            
              > *python {determine_script} --django-settings-module mysettings --apps-file * --known-models-file * --scratch-path *
              |
              | Traceback (most recent call last):
              |   File "{determine_script}", line 8, in <module>
              |     raise ValueError("Computer says no")
              | ValueError: Computer says no
              |
            """,
        )

    def test_gracefully_handles_determine_version_failure_on_subsequent_run(
        self, scenario: Scenario, tmp_path: pathlib.Path
    ) -> None:
        if not scenario.for_daemon:
            pytest.skip("Test only relevant for the daemon")

        determine_script = tmp_path / "determine.py"

        determine_script.write_text(
            textwrap.dedent("""
        #!/usr/bin/env python

        from extended_mypy_django_plugin.scripts.determine_django_state import main


        if __name__ == "__main__":
            main()
        """)
        )

        os.chmod(determine_script, 0o755)
        scenario.scenario.additional_mypy_config += (
            f"\ndetermine_django_state_script = {determine_script}"
        )

        @scenario.run_and_check_mypy_after
        def _(expected: OutputBuilder) -> None:
            pass

        determine_script.write_text(
            textwrap.dedent("""
        #!/usr/bin/env python

        from extended_mypy_django_plugin.scripts.determine_django_state import main


        if __name__ == "__main__":
            raise ValueError("Computer says no")
            main()
        """)
        )

        called: list[int] = []

        class CheckNoCrashShowsFailure(OutputChecker):
            def check(self, ret_code: int, stdout: str, stderr: str) -> None:
                called.append(ret_code)

                assert ret_code == 0
                assertions.assert_glob_lines(
                    stdout + stderr,
                    f"""
                    Failed to determine information about the django setup
                    
                    > */python {determine_script} --django-settings-module mysettings --apps-file * --known-models-file * --scratch-path *
                    |
                    | Traceback (most recent call last):
                    |   File "{determine_script}", line 8, in <module>
                    |     raise ValueError("Computer says no")
                    | ValueError: Computer says no
                    |
                    """,
                )

        scenario.run_and_check_mypy(scenario.expected, OutputCheckerKls=CheckNoCrashShowsFailure)
        assert called == [0]

        determine_script.write_text(
            textwrap.dedent("""
        #!/usr/bin/env python

        from extended_mypy_django_plugin.scripts.determine_django_state import main


        if __name__ == "__main__":
            main()
        """)
        )

        class CheckNoOutput(OutputChecker):
            def check(self, ret_code: int, stdout: str, stderr: str) -> None:
                called.append(ret_code)

                assert ret_code == 0
                assert stdout + stderr == ""

        scenario.run_and_check_mypy(scenario.expected, OutputCheckerKls=CheckNoOutput)
        assert called == [0, 0]
