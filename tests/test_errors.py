from extended_mypy_django_plugin_test_driver import OutputBuilder, Scenario


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
