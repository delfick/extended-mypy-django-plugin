import dataclasses
from collections.abc import Sequence

from extended_mypy_django_plugin.django_analysis import (
    ImportPath,
    Project,
    protocols,
    virtual_dependencies,
)


class TestVirtualDependency:
    def test_making_virtual_dependency(
        self, discovered_django_example: protocols.Discovered[Project]
    ) -> None:
        import djangoexample.exampleapp.models

        module = discovered_django_example.installed_models_modules[
            ImportPath.from_module(djangoexample.exampleapp.models)
        ]

        related_models: set[protocols.ImportPath] = {
            ImportPath("djangoexample.exampleapp.models.Child3"),
            ImportPath("djangoexample.exampleapp.models.Parent"),
            ImportPath("djangoexample.exampleapp.models.Child2"),
            ImportPath("djangoexample.exampleapp.models.Child1"),
            ImportPath("djangoexample.exampleapp.models.Parent2"),
            ImportPath("djangoexample.exampleapp.models.Child4"),
        }
        custom_querysets: set[protocols.ImportPath] = {
            ImportPath("djangoexample.exampleapp.models.Child2QuerySet"),
            ImportPath("djangoexample.exampleapp.models.Child4QuerySet"),
        }

        def hasher(*parts: bytes) -> str:
            if parts == tuple(
                model.encode() for model in sorted(related_models | custom_querysets)
            ):
                return "__hashed_related_models__"
            else:
                raise AssertionError("unexpected use of the hasher")

        def namer(module: protocols.ImportPath, /) -> protocols.ImportPath:
            return ImportPath(f"__virtual__.mod_{module.replace('.','_')}")

        virtual_dependency = virtual_dependencies.VirtualDependency.create(
            discovered_project=discovered_django_example,
            module=module,
            hasher=hasher,
            virtual_dependency_namer=namer,
            installed_apps_hash="__hashed_installed_apps__",
            make_differentiator=lambda: "__DIFFERENTIATOR__",
        )

        all_models = discovered_django_example.all_models

        assert virtual_dependency == virtual_dependencies.VirtualDependency(
            module=module,
            interface_differentiator="__DIFFERENTIATOR__",
            summary=virtual_dependencies.VirtualDependencySummary(
                virtual_dependency_name=ImportPath(
                    "__virtual__.mod_djangoexample_exampleapp_models"
                ),
                module_import_path=module.import_path,
                installed_apps_hash="__hashed_installed_apps__",
                significant_objects_hash="__hashed_related_models__",
            ),
            all_related_models=sorted(related_models),
            concrete_models={
                ImportPath("djangoexample.exampleapp.models.Parent"): [
                    all_models[ImportPath("djangoexample.exampleapp.models.Child1")],
                    all_models[ImportPath("djangoexample.exampleapp.models.Child2")],
                    all_models[ImportPath("djangoexample.exampleapp.models.Child3")],
                    all_models[ImportPath("djangoexample.exampleapp.models.Child4")],
                    all_models[ImportPath("djangoexample.exampleapp2.models.ChildOther")],
                    all_models[ImportPath("djangoexample.exampleapp2.models.ChildOther2")],
                ],
                ImportPath("djangoexample.exampleapp.models.Parent2"): [
                    all_models[ImportPath("djangoexample.exampleapp.models.Child3")],
                    all_models[ImportPath("djangoexample.exampleapp.models.Child4")],
                ],
                ImportPath("djangoexample.exampleapp.models.Child1"): [
                    all_models[ImportPath("djangoexample.exampleapp.models.Child1")]
                ],
                ImportPath("djangoexample.exampleapp.models.Child2"): [
                    all_models[ImportPath("djangoexample.exampleapp.models.Child2")]
                ],
                ImportPath("djangoexample.exampleapp.models.Child3"): [
                    all_models[ImportPath("djangoexample.exampleapp.models.Child3")]
                ],
                ImportPath("djangoexample.exampleapp.models.Child4"): [
                    all_models[ImportPath("djangoexample.exampleapp.models.Child4")]
                ],
            },
        )

    def test_making_uninstalled_virtual_dependency(
        self, discovered_django_example: protocols.Discovered[Project]
    ) -> None:
        @dataclasses.dataclass(frozen=True, kw_only=True)
        class FakeModel:
            model_name: str = "MyModel"
            module_import_path: protocols.ImportPath = dataclasses.field(
                default_factory=lambda: ImportPath("fake.model")
            )
            import_path: protocols.ImportPath = dataclasses.field(
                default_factory=lambda: ImportPath("fake.model.MyModel")
            )
            is_abstract: bool = False
            default_custom_queryset: protocols.ImportPath | None = None
            all_fields: protocols.FieldsMap = dataclasses.field(default_factory=dict)
            models_in_mro: Sequence[protocols.ImportPath] = dataclasses.field(default_factory=list)

        @dataclasses.dataclass(frozen=True, kw_only=True)
        class FakeModule:
            installed: bool = False
            import_path: protocols.ImportPath = dataclasses.field(
                default_factory=lambda: ImportPath("fake.model")
            )
            defined_models: protocols.ModelMap = dataclasses.field(
                default_factory=lambda: {fake_model.import_path: fake_model}
            )
            models_hash: str = ""

        fake_model: protocols.Model = FakeModel()
        fake_module: protocols.Module = FakeModule()

        def hasher(*parts: bytes) -> str:
            raise AssertionError("shouldn't be used")

        def make_differentiator() -> str:
            raise AssertionError("shouldn't be used")

        def namer(module: protocols.ImportPath, /) -> protocols.ImportPath:
            return ImportPath(f"__virtual__.mod_{module.replace('.','_')}")

        virtual_dependency = virtual_dependencies.VirtualDependency.create(
            discovered_project=discovered_django_example,
            module=fake_module,
            hasher=hasher,
            virtual_dependency_namer=namer,
            installed_apps_hash="__hashed_installed_apps__",
            make_differentiator=make_differentiator,
        )

        assert virtual_dependency == virtual_dependencies.VirtualDependency(
            module=fake_module,
            interface_differentiator=None,
            summary=virtual_dependencies.VirtualDependencySummary(
                virtual_dependency_name=ImportPath("__virtual__.mod_fake_model"),
                module_import_path=fake_module.import_path,
                installed_apps_hash=None,
                significant_objects_hash=None,
            ),
            all_related_models=[],
            concrete_models={},
        )
