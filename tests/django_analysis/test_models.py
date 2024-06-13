from __future__ import annotations

import dataclasses
import functools

import pytest
from typing_extensions import Self

from extended_mypy_django_plugin.django_analysis import Model, Module, protocols


@pytest.fixture(autouse=True)
def _ensure_django_loaded(loaded_django_example: protocols.LoadedProject) -> None:
    """
    Make sure the loaded_django_example fixture is active so that we can import our djangoexample models inside tests
    """


@dataclasses.dataclass
class EmptyField:
    @classmethod
    def create(
        cls, *, model_import_path: protocols.ImportPath, field: protocols.DjangoField
    ) -> Self:
        return cls(model_import_path=model_import_path, field=field)

    model_import_path: protocols.ImportPath
    field: protocols.DjangoField

    field_type: protocols.ImportPath = dataclasses.field(
        default_factory=lambda: protocols.ImportPath("")
    )
    directly_related_models: set[protocols.ImportPath] = dataclasses.field(default_factory=set)


class TestModule:
    def test_interpreting_a_module(self) -> None:
        import djangoexample.exampleapp.models

        module_import_path = protocols.ImportPath("djangoexample.exampleapp.models")

        module = Module.create(
            model_creator=functools.partial(Model.create, field_creator=EmptyField.create),
            import_path=module_import_path,
            module=(mod := djangoexample.exampleapp.models),
            models=[mod.Parent, mod.Child1],
        )

        defined_models = [
            Model(
                model_name="Parent",
                module_import_path=module_import_path,
                import_path=(mip := protocols.ImportPath(f"{module_import_path}.Parent")),
                is_abstract=True,
                default_custom_queryset=None,
                all_fields={
                    "one": EmptyField(
                        model_import_path=mip, field=mod.Parent._meta.get_field("one")
                    ),
                },
            ),
            Model(
                model_name="Child1",
                module_import_path=module_import_path,
                import_path=(mip := protocols.ImportPath(f"{module_import_path}.Child1")),
                is_abstract=False,
                default_custom_queryset=None,
                all_fields={
                    "id": EmptyField(
                        model_import_path=mip, field=mod.Child1._meta.get_field("id")
                    ),
                    "one": EmptyField(
                        model_import_path=mip, field=mod.Child1._meta.get_field("one")
                    ),
                    "two": EmptyField(
                        model_import_path=mip, field=mod.Child1._meta.get_field("two")
                    ),
                },
            ),
        ]

        assert module == Module(
            installed=True,
            import_path=protocols.ImportPath("djangoexample.exampleapp.models"),
            defined_models_by_name={model.import_path: model for model in defined_models},
        )


class TestModel:
    def test_it_can_interpret_an_abstract_model(self) -> None:
        import djangoexample.exampleapp.models

        mod = djangoexample.exampleapp.models

        expected = Model(
            model_name="Parent",
            module_import_path=(
                module_import_path := protocols.ImportPath("djangoexample.exampleapp.models")
            ),
            import_path=(mip := protocols.ImportPath(f"{module_import_path}.Parent")),
            is_abstract=True,
            default_custom_queryset=None,
            all_fields={
                "one": EmptyField(model_import_path=mip, field=mod.Parent._meta.get_field("one")),
            },
        )

        assert (
            Model.create(
                field_creator=EmptyField.create, model=djangoexample.exampleapp.models.Parent
            )
            == expected
        )

    def test_it_can_interpret_a_model_with_a_custom_queryset(self) -> None:
        import djangoexample.exampleapp.models

        mod = djangoexample.exampleapp.models

        expected = Model(
            model_name="Child2",
            module_import_path=(
                module_import_path := protocols.ImportPath("djangoexample.exampleapp.models")
            ),
            import_path=(mip := protocols.ImportPath(f"{module_import_path}.Child2")),
            is_abstract=False,
            default_custom_queryset=protocols.ImportPath(
                "djangoexample.exampleapp.models.Child2QuerySet"
            ),
            all_fields={
                "id": EmptyField(model_import_path=mip, field=mod.Child2._meta.get_field("id")),
                "one": EmptyField(model_import_path=mip, field=mod.Child2._meta.get_field("one")),
                "two": EmptyField(model_import_path=mip, field=mod.Child2._meta.get_field("two")),
                "four": EmptyField(
                    model_import_path=mip, field=mod.Child2._meta.get_field("four")
                ),
                "three": EmptyField(
                    model_import_path=mip, field=mod.Child2._meta.get_field("three")
                ),
            },
        )

        assert (
            Model.create(
                field_creator=EmptyField.create, model=djangoexample.exampleapp.models.Child2
            )
            == expected
        )

    def test_it_can_interpret_a_model_without_a_custom_queryset(self) -> None:
        import djangoexample.exampleapp.models

        mod = djangoexample.exampleapp.models

        expected = Model(
            model_name="Child1",
            module_import_path=(
                module_import_path := protocols.ImportPath("djangoexample.exampleapp.models")
            ),
            import_path=(mip := protocols.ImportPath(f"{module_import_path}.Child1")),
            is_abstract=False,
            default_custom_queryset=None,
            all_fields={
                "id": EmptyField(model_import_path=mip, field=mod.Child1._meta.get_field("id")),
                "one": EmptyField(model_import_path=mip, field=mod.Child1._meta.get_field("one")),
                "two": EmptyField(model_import_path=mip, field=mod.Child1._meta.get_field("two")),
            },
        )

        assert (
            Model.create(
                field_creator=EmptyField.create, model=djangoexample.exampleapp.models.Child1
            )
            == expected
        )
