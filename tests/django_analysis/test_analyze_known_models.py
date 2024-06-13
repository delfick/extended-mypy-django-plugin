import dataclasses
import types
from collections.abc import Sequence

from django.db import models

from extended_mypy_django_plugin.django_analysis import analyzers, protocols


class TestKnownModelsAnalyzer:
    def test_it_finds_modules_that_have_models(
        self, loaded_django_example: protocols.LoadedProject
    ) -> None:
        @dataclasses.dataclass
        class Module:
            @classmethod
            def create(
                cls,
                *,
                import_path: protocols.ImportPath,
                module: types.ModuleType | None,
                models: Sequence[type[models.Model]],
            ) -> protocols.Module:
                return cls(
                    installed=module is not None,
                    import_path=import_path,
                    module=module,
                    models=models,
                )

            installed: bool
            module: types.ModuleType | None
            models: Sequence[type[models.Model]]
            import_path: protocols.ImportPath
            defined_models_by_name: protocols.DefinedModelsMap = dataclasses.field(
                default_factory=dict
            )

        known_modules = analyzers.KnownModelsAnalyzer(module_creator=Module.create)(
            loaded_django_example
        )

        import django.contrib.admin.models
        import django.contrib.auth.models
        import django.contrib.contenttypes.models
        import django.contrib.sessions.models
        import djangoexample.exampleapp.models
        import djangoexample.exampleapp2.models
        import djangoexample.only_abstract.models

        IP = protocols.ImportPath
        expected = [
            Module(
                installed=True,
                import_path=IP("django.contrib.admin.models"),
                module=(mod := django.contrib.admin.models),
                models=[mod.LogEntry],
            ),
            Module(
                installed=True,
                import_path=IP("django.contrib.auth.models"),
                module=(mod := django.contrib.auth.models),
                models=[
                    mod.AbstractUser,
                    mod.PermissionsMixin,
                    mod.Permission,
                    mod.Group,
                    mod.User,
                ],
            ),
            Module(
                installed=True,
                import_path=IP("django.contrib.contenttypes.models"),
                module=(mod := django.contrib.contenttypes.models),
                models=[mod.ContentType],
            ),
            Module(
                installed=True,
                import_path=IP("django.contrib.sessions.models"),
                module=(mod := django.contrib.sessions.models),
                models=[mod.Session],
            ),
            Module(
                installed=True,
                import_path=IP("djangoexample.exampleapp.models"),
                module=(mod := djangoexample.exampleapp.models),
                models=[mod.Parent, mod.Parent2, mod.Child1, mod.Child2, mod.Child3, mod.Child4],
            ),
            Module(
                installed=True,
                import_path=IP("djangoexample.exampleapp2.models"),
                module=(mod := djangoexample.exampleapp2.models),
                models=[mod.ChildOther, mod.ChildOther2],
            ),
            Module(
                installed=True,
                import_path=IP("djangoexample.only_abstract.models"),
                module=(mod := djangoexample.only_abstract.models),
                models=[mod.AnAbstract],
            ),
            # # There is no way for our discovery to know about these without some kind of invasive
            # # traversal of every file in site-packages. We do know about them at mypy time and create
            # # virtual dependencies for them when they are seen. We also can't import them without them
            # # being installed because you can't create a model class on an app that is not installed
            # # So any code that depends on the annotations that would go into the virtual dependencies
            # # cannot import the models the annotations would be used with so this is fine
            # Module(
            #     installed=False,
            #     import_path=IP("djangoexample.not_installed_only_abstract.models"),
            #     module=None,
            #     models=[],
            # ),
            # Module(
            #     installed=False,
            #     import_path=IP("djangoexample.not_installed_with_concrete.models"),
            #     module=None,
            #     models=[],
            # ),
        ]
        assert known_modules == {m.import_path: m for m in expected}
