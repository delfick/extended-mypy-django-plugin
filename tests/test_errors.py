import importlib.metadata

from extended_mypy_django_plugin_test_driver import OutputBuilder, Scenario


class TestErrors:
    def test_cant_use_typevar_concrete_annotation_in_function_or_method_typeguard(
        self, scenario: Scenario
    ) -> None:
        @scenario.run_and_check_mypy_after
        def _(expected: OutputBuilder) -> None:
            scenario.make_file(
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
                reveal_type(cls1)

                def function_with_instance_typeguard(
                    instance: T_Parent
                ) -> TypeGuard[Concrete[T_Parent]]:
                    return True

                instance1: Parent = cast(Child1, None)
                assert function_with_instance_typeguard(instance1)
                reveal_type(instance1)

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
                reveal_type(cls2)

                instance2: Parent = cast(Child1, None)
                assert logic.method_with_instance_typeguard(instance2)
                reveal_type(instance2)
                """,
            )

            out = """
            main:15: error: Can't use a TypeGuard that uses a Concrete Annotation that uses type variables  [misc]
            main:16: note: Revealed type is "type[extended_mypy_django_plugin.annotations.Concrete[myapp.models.Parent]]"
            main:24: error: Can't use a TypeGuard that uses a Concrete Annotation that uses type variables  [misc]
            main:25: note: Revealed type is "extended_mypy_django_plugin.annotations.Concrete[myapp.models.Parent]"
            main:40: error: Can't use a TypeGuard that uses a Concrete Annotation that uses type variables  [misc]
            main:41: note: Revealed type is "type[extended_mypy_django_plugin.annotations.Concrete[T_Parent`-1]]"
            main:44: error: Can't use a TypeGuard that uses a Concrete Annotation that uses type variables  [misc]
            main:45: note: Revealed type is "extended_mypy_django_plugin.annotations.Concrete[T_Parent`-1]"
            """

            if importlib.metadata.version("mypy") == "1.4.0":
                out = "\n".join(
                    line
                    for line in out.split("\n")
                    if "Only concrete class can be given" not in line
                )

            expected.from_out(out)
