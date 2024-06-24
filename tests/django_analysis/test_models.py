from __future__ import annotations

import dataclasses
import functools

import pytest
from typing_extensions import Self

from extended_mypy_django_plugin.django_analysis import (
    Field,
    ImportPath,
    Model,
    Module,
    Project,
    protocols,
)


@pytest.fixture(autouse=True)
def _ensure_django_loaded(loaded_django_example: protocols.Loaded[Project]) -> None:
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

    def __post_init__(self) -> None:
        self.field_type = ImportPath.from_cls(self.field.__class__)

    model_import_path: protocols.ImportPath
    field: protocols.DjangoField

    field_type: protocols.ImportPath = dataclasses.field(init=False)
    related_model: protocols.ImportPath | None = None


class TestModule:
    def test_interpreting_a_module(self) -> None:
        import djangoexample.exampleapp.models

        module_import_path = ImportPath("djangoexample.exampleapp.models")

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
                import_path=(mip := ImportPath(f"{module_import_path}.Parent")),
                is_abstract=True,
                default_custom_queryset=None,
                all_fields={
                    "one": EmptyField(
                        model_import_path=mip, field=mod.Parent._meta.get_field("one")
                    ),
                },
                models_in_mro=[],
            ),
            Model(
                model_name="Child1",
                module_import_path=module_import_path,
                import_path=(mip := ImportPath(f"{module_import_path}.Child1")),
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
                models_in_mro=[
                    ImportPath("djangoexample.exampleapp.models.Parent"),
                ],
            ),
        ]

        assert module == Module(
            import_path=ImportPath("djangoexample.exampleapp.models"),
            defined_models={model.import_path: model for model in defined_models},
        )


class TestModel:
    def test_it_can_interpret_an_abstract_model(self) -> None:
        import djangoexample.exampleapp.models

        mod = djangoexample.exampleapp.models

        expected = Model(
            model_name="Parent",
            module_import_path=(
                module_import_path := ImportPath("djangoexample.exampleapp.models")
            ),
            import_path=(mip := ImportPath(f"{module_import_path}.Parent")),
            is_abstract=True,
            default_custom_queryset=None,
            all_fields={
                "one": EmptyField(model_import_path=mip, field=mod.Parent._meta.get_field("one")),
            },
            models_in_mro=[],
        )

        assert (
            Model.create(
                field_creator=EmptyField.create, model=djangoexample.exampleapp.models.Parent
            )
            == expected
        )

    def test_it_can_find_multiple_parent_models(self) -> None:
        import djangoexample.exampleapp.models

        made = Model.create(
            field_creator=EmptyField.create, model=djangoexample.exampleapp.models.Child3
        )

        assert made.models_in_mro == [
            ImportPath("djangoexample.exampleapp.models.Parent2"),
            ImportPath("djangoexample.exampleapp.models.Parent"),
        ]

    def test_it_can_interpret_a_model_with_a_custom_queryset(self) -> None:
        import djangoexample.exampleapp.models

        mod = djangoexample.exampleapp.models

        expected = Model(
            model_name="Child2",
            module_import_path=(
                module_import_path := ImportPath("djangoexample.exampleapp.models")
            ),
            import_path=(mip := ImportPath(f"{module_import_path}.Child2")),
            is_abstract=False,
            default_custom_queryset=ImportPath("djangoexample.exampleapp.models.Child2QuerySet"),
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
            models_in_mro=[ImportPath("djangoexample.exampleapp.models.Parent")],
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
                module_import_path := ImportPath("djangoexample.exampleapp.models")
            ),
            import_path=(mip := ImportPath(f"{module_import_path}.Child1")),
            is_abstract=False,
            default_custom_queryset=None,
            all_fields={
                "id": EmptyField(model_import_path=mip, field=mod.Child1._meta.get_field("id")),
                "one": EmptyField(model_import_path=mip, field=mod.Child1._meta.get_field("one")),
                "two": EmptyField(model_import_path=mip, field=mod.Child1._meta.get_field("two")),
            },
            models_in_mro=[ImportPath("djangoexample.exampleapp.models.Parent")],
        )

        assert (
            Model.create(
                field_creator=EmptyField.create, model=djangoexample.exampleapp.models.Child1
            )
            == expected
        )

    def test_it_can_see_reverse_relationships(self) -> None:
        import djangoexample.relations1.models

        mod = djangoexample.relations1.models

        expected = Model(
            model_name="Concrete1",
            module_import_path=(
                module_import_path := ImportPath("djangoexample.relations1.models")
            ),
            import_path=(mip := ImportPath(f"{module_import_path}.Concrete1")),
            is_abstract=False,
            default_custom_queryset=ImportPath(
                "djangoexample.relations1.models.Concrete1QuerySet"
            ),
            all_fields={
                "id": EmptyField(model_import_path=mip, field=mod.Concrete1._meta.get_field("id")),
                "c2s": EmptyField(
                    model_import_path=mip, field=mod.Concrete1._meta.fields_map["c2s"]
                ),
                "thing": EmptyField(
                    model_import_path=mip, field=mod.Concrete1._meta.fields_map["thing"]
                ),
            },
            models_in_mro=[],
        )

        assert (
            Model.create(
                field_creator=EmptyField.create, model=djangoexample.relations1.models.Concrete1
            )
            == expected
        )

    def test_it_can_see_forward_relationships(self) -> None:
        import djangoexample.relations1.models

        mod = djangoexample.relations1.models

        expected = Model(
            model_name="Concrete2",
            module_import_path=(
                module_import_path := ImportPath("djangoexample.relations1.models")
            ),
            import_path=(mip := ImportPath(f"{module_import_path}.Concrete2")),
            is_abstract=False,
            default_custom_queryset=None,
            all_fields={
                "id": EmptyField(model_import_path=mip, field=mod.Concrete2._meta.get_field("id")),
                "concrete1": EmptyField(
                    model_import_path=mip, field=mod.Concrete2._meta.get_field("concrete1")
                ),
                "children": EmptyField(
                    model_import_path=mip, field=mod.Concrete2._meta.get_field("children")
                ),
                "Concrete2_children+": EmptyField(
                    model_import_path=mip,
                    field=mod.Concrete2._meta.fields_map["Concrete2_children+"],
                ),
            },
            models_in_mro=[],
        )

        assert (
            Model.create(
                field_creator=EmptyField.create, model=djangoexample.relations1.models.Concrete2
            )
            == expected
        )


class TestField:
    def test_it_can_interpret_a_plain_field(self) -> None:
        import djangoexample.exampleapp.models

        mod = djangoexample.exampleapp.models

        field = Field.create(
            model_import_path=(mip := ImportPath("djangoexample.exampleapp.models.Child2")),
            field=mod.Child2._meta.get_field("one"),
        )

        assert field == Field(
            model_import_path=mip,
            field_type=ImportPath("django.db.models.fields.CharField"),
            related_model=None,
        )

    def test_it_can_see_reverse_related_fields(self) -> None:
        import djangoexample.relations1.models

        mod = djangoexample.relations1.models

        field = Field.create(
            model_import_path=(mip := ImportPath("djangoexample.relations1.models.Concrete1")),
            field=mod.Concrete1._meta.fields_map["thing"],
        )

        assert field == Field(
            model_import_path=mip,
            field_type=ImportPath("django.db.models.fields.reverse_related.OneToOneRel"),
            related_model=ImportPath("djangoexample.relations2.models.Thing"),
        )

    def test_it_can_see_many_to_many_relations(self) -> None:
        import djangoexample.relations1.models

        mod = djangoexample.relations1.models

        field = Field.create(
            model_import_path=(mip := ImportPath("djangoexample.relations1.models.Concrete2")),
            field=mod.Concrete2._meta.get_field("children"),
        )

        assert field == Field(
            model_import_path=mip,
            field_type=ImportPath("django.db.models.fields.related.ManyToManyField"),
            related_model=ImportPath("djangoexample.relations1.models.Child1"),
        )

    def test_it_can_see_many_to_many_relations_hidden_field(self) -> None:
        import djangoexample.relations1.models

        mod = djangoexample.relations1.models

        field = Field.create(
            model_import_path=(mip := ImportPath("djangoexample.relations1.models.Concrete2")),
            field=mod.Concrete2._meta.fields_map["Concrete2_children+"],
        )

        assert field == Field(
            model_import_path=mip,
            field_type=ImportPath("django.db.models.fields.reverse_related.ManyToOneRel"),
            # Empty because it refers to a many to many model class that doesn't exist
            related_model=None,
        )

    def test_it_can_see_forieng_key(self) -> None:
        import djangoexample.relations1.models

        mod = djangoexample.relations1.models

        field = Field.create(
            model_import_path=(mip := ImportPath("djangoexample.relations1.models.Concrete2")),
            field=mod.Concrete2._meta.get_field("concrete1"),
        )

        assert field == Field(
            model_import_path=mip,
            field_type=ImportPath("django.db.models.fields.related.ForeignKey"),
            related_model=ImportPath("djangoexample.relations1.models.Concrete1"),
        )
