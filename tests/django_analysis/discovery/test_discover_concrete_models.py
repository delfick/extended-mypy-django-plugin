from django.db import models

from extended_mypy_django_plugin.django_analysis import (
    Field,
    ImportPath,
    Model,
    Project,
    discovery,
    protocols,
)


class TestConcreteModelsDiscovery:
    def test_it_collects_concrete_models(
        self, loaded_django_example: protocols.Loaded[Project]
    ) -> None:
        import djangoexample.exampleapp.models as mod
        import djangoexample.exampleapp2.models as mod2

        made: dict[type[models.Model], protocols.Model] = {}

        def create_model(model: type[models.Model]) -> protocols.Model:
            created = Model.create(field_creator=Field.create, model=model)
            made[model] = created
            return created

        all_models = {
            ImportPath.from_cls(model): create_model(model)
            for model in [
                mod.Parent,
                mod.Parent2,
                mod.Child1,
                mod.Child2,
                mod.Child3,
                mod.Child4,
                mod2.ChildOther,
                mod2.ChildOther2,
            ]
        }
        concrete_models = discovery.ConcreteModelsDiscovery[Project]()(
            loaded_django_example, all_models
        )

        assert concrete_models == {
            ImportPath.from_cls(mod.Parent): [
                made[mod.Child1],
                made[mod.Child2],
                made[mod.Child3],
                made[mod.Child4],
                made[mod2.ChildOther],
                made[mod2.ChildOther2],
            ],
            ImportPath.from_cls(mod.Parent2): [
                made[mod.Child3],
                made[mod.Child4],
            ],
            ImportPath.from_cls(mod.Child1): [made[mod.Child1]],
            ImportPath.from_cls(mod.Child2): [made[mod.Child2]],
            ImportPath.from_cls(mod.Child3): [made[mod.Child3]],
            ImportPath.from_cls(mod.Child4): [made[mod.Child4]],
            ImportPath.from_cls(mod2.ChildOther): [made[mod2.ChildOther]],
            ImportPath.from_cls(mod2.ChildOther2): [made[mod2.ChildOther2]],
        }
