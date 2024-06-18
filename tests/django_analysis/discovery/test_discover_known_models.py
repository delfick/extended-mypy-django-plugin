import dataclasses
import types
from collections.abc import Sequence
from unittest import mock

from django.db import models

from extended_mypy_django_plugin.django_analysis import ImportPath, Project, discovery, protocols


class TestKnownModelsDiscovery:
    def test_it_finds_modules_that_have_models(
        self, loaded_django_example: protocols.Loaded[Project]
    ) -> None:
        @dataclasses.dataclass
        class ExampleModule:
            @classmethod
            def create(
                cls,
                *,
                import_path: protocols.ImportPath,
                module: types.ModuleType | None,
                models: Sequence[type[models.Model]],
            ) -> protocols.Module:
                defined_models = discovery.make_module_creator()(
                    import_path=import_path, module=module, models=models
                ).defined_models
                return cls(
                    installed=module is not None,
                    import_path=import_path,
                    module=module,
                    models=models,
                    defined_models=defined_models,
                )

            installed: bool
            module: types.ModuleType | None
            models: Sequence[type[models.Model]]
            import_path: protocols.ImportPath
            defined_models: protocols.ModelMap

        known_modules = discovery.DefaultInstalledModulesDiscovery[Project](
            module_creator=ExampleModule.create
        )(loaded_django_example)

        import django.contrib.admin.models
        import django.contrib.auth.base_user
        import django.contrib.auth.models
        import django.contrib.contenttypes.models
        import django.contrib.sessions.base_session
        import django.contrib.sessions.models
        import djangoexample.empty_models.models
        import djangoexample.exampleapp.models
        import djangoexample.exampleapp2.models
        import djangoexample.only_abstract.models
        import djangoexample.relations1.models
        import djangoexample.relations2.models

        expected = [
            ExampleModule(
                installed=True,
                import_path=ImportPath("django.contrib.admin.models"),
                module=(mod := django.contrib.admin.models),
                models=[mod.LogEntry],
                defined_models=mock.ANY,
            ),
            ExampleModule(
                installed=True,
                import_path=ImportPath("django.contrib.auth.models"),
                module=(mod := django.contrib.auth.models),
                models=[
                    mod.AbstractUser,
                    mod.PermissionsMixin,
                    mod.Permission,
                    mod.Group,
                    mod.User,
                ],
                defined_models=mock.ANY,
            ),
            ExampleModule(
                installed=True,
                import_path=ImportPath("django.contrib.contenttypes.models"),
                module=(mod := django.contrib.contenttypes.models),
                models=[mod.ContentType],
                defined_models=mock.ANY,
            ),
            ExampleModule(
                installed=True,
                import_path=ImportPath("django.contrib.sessions.models"),
                module=(mod := django.contrib.sessions.models),
                models=[mod.Session],
                defined_models=mock.ANY,
            ),
            ExampleModule(
                installed=True,
                import_path=ImportPath("djangoexample.exampleapp.models"),
                module=(mod := djangoexample.exampleapp.models),
                models=[mod.Parent, mod.Parent2, mod.Child1, mod.Child2, mod.Child3, mod.Child4],
                defined_models=mock.ANY,
            ),
            ExampleModule(
                installed=True,
                import_path=ImportPath("djangoexample.exampleapp2.models"),
                module=(mod := djangoexample.exampleapp2.models),
                models=[mod.ChildOther, mod.ChildOther2],
                defined_models=mock.ANY,
            ),
            ExampleModule(
                installed=True,
                import_path=ImportPath("djangoexample.only_abstract.models"),
                module=(mod := djangoexample.only_abstract.models),
                models=[mod.AnAbstract],
                defined_models=mock.ANY,
            ),
            ExampleModule(
                installed=True,
                import_path=ImportPath("djangoexample.relations1.models"),
                module=(mod := djangoexample.relations1.models),
                models=[mod.Abstract, mod.Child1, mod.Child2, mod.Concrete1, mod.Concrete2],
                defined_models=mock.ANY,
            ),
            ExampleModule(
                installed=True,
                import_path=ImportPath("djangoexample.relations2.models"),
                module=(mod := djangoexample.relations2.models),
                models=[mod.Thing],
                defined_models=mock.ANY,
            ),
            ExampleModule(
                installed=True,
                import_path=ImportPath("djangoexample.empty_models.models"),
                module=(mod := djangoexample.empty_models.models),
                models=[],
                defined_models={},
            ),
            # # There is no way for our discovery to know about these without some kind of invasive
            # # traversal of every file in site-packages. We do know about them at mypy time and create
            # # virtual dependencies for them when they are seen. We also can't import them without them
            # # being installed because you can't create a model class on an app that is not installed
            # # So any code that depends on the annotations that would go into the virtual dependencies
            # # cannot import the models the annotations would be used with so this is fine
            # Module(
            #     installed=False,
            #     import_path=ImportPath("djangoexample.not_installed_only_abstract.models"),
            #     module=None,
            #     models=[],
            #     defined_models=mock.ANY,
            # ),
            # Module(
            #     installed=False,
            #     import_path=ImportPath("djangoexample.not_installed_with_concrete.models"),
            #     module=None,
            #     models=[],
            #     defined_models=mock.ANY,
            # ),
            ###
            ## Indirect modules
            ###
            ExampleModule(
                installed=True,
                import_path=ImportPath("django.contrib.auth.base_user"),
                module=(mod := django.contrib.auth.base_user),
                models=[mod.AbstractBaseUser],
                defined_models=mock.ANY,
            ),
            ExampleModule(
                installed=True,
                import_path=ImportPath("django.contrib.sessions.base_session"),
                module=(mod := django.contrib.sessions.base_session),
                models=[mod.AbstractBaseSession],
                defined_models=mock.ANY,
            ),
        ]
        assert known_modules == {m.import_path: m for m in expected}
