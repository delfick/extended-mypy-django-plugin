import dataclasses

from extended_mypy_django_plugin.django_analysis import (
    ImportPath,
    Project,
    protocols,
    virtual_dependencies,
)


@dataclasses.dataclass
class Namer:
    namespace: protocols.ImportPath = dataclasses.field(
        default_factory=lambda: ImportPath("__virtual__")
    )

    def __call__(self, module: protocols.ImportPath, /) -> protocols.ImportPath:
        return ImportPath(f"{self.namespace}.mod_{module.replace('.','_')}")


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

        significant_info = [
            "module:djangoexample.exampleapp.models",
            "module:djangoexample.exampleapp.models>concrete:djangoexample.exampleapp.models.Parent=djangoexample.exampleapp.models.Child1,djangoexample.exampleapp.models.Child2,djangoexample.exampleapp.models.Child3,djangoexample.exampleapp.models.Child4,djangoexample.exampleapp2.models.ChildOther,djangoexample.exampleapp2.models.ChildOther2",
            "module:djangoexample.exampleapp.models>concrete:djangoexample.exampleapp.models.Parent2=djangoexample.exampleapp.models.Child3,djangoexample.exampleapp.models.Child4",
            "module:djangoexample.exampleapp.models>concrete:djangoexample.exampleapp.models.Child1=djangoexample.exampleapp.models.Child1",
            "module:djangoexample.exampleapp.models>concrete:djangoexample.exampleapp.models.Child2=djangoexample.exampleapp.models.Child2",
            "module:djangoexample.exampleapp.models>concrete:djangoexample.exampleapp.models.Child3=djangoexample.exampleapp.models.Child3",
            "module:djangoexample.exampleapp.models>concrete:djangoexample.exampleapp.models.Child4=djangoexample.exampleapp.models.Child4",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Parent>is_abstract:True",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Parent>field:one",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Parent>field:one>field_type:django.db.models.fields.CharField",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Parent2>is_abstract:True",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Parent2>mro_0:djangoexample.exampleapp.models.Parent",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Parent2>field:one",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Parent2>field:one>field_type:django.db.models.fields.CharField",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Parent2>field:three",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Parent2>field:three>field_type:django.db.models.fields.CharField",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child1>is_abstract:False",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child1>mro_0:djangoexample.exampleapp.models.Parent",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child1>field:id",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child1>field:id>field_type:django.db.models.fields.BigAutoField",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child1>field:one",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child1>field:one>field_type:django.db.models.fields.CharField",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child1>field:two",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child1>field:two>field_type:django.db.models.fields.CharField",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child2>is_abstract:False",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child2>custom_queryset:djangoexample.exampleapp.models.Child2QuerySet",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child2>mro_0:djangoexample.exampleapp.models.Parent",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child2>field:id",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child2>field:id>field_type:django.db.models.fields.BigAutoField",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child2>field:one",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child2>field:one>field_type:django.db.models.fields.CharField",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child2>field:two",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child2>field:two>field_type:django.db.models.fields.CharField",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child2>field:four",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child2>field:four>field_type:django.db.models.fields.CharField",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child2>field:three",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child2>field:three>field_type:django.db.models.fields.CharField",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child3>is_abstract:False",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child3>mro_0:djangoexample.exampleapp.models.Parent2",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child3>mro_1:djangoexample.exampleapp.models.Parent",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child3>field:id",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child3>field:id>field_type:django.db.models.fields.BigAutoField",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child3>field:one",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child3>field:one>field_type:django.db.models.fields.CharField",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child3>field:two",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child3>field:two>field_type:django.db.models.fields.CharField",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child3>field:three",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child3>field:three>field_type:django.db.models.fields.CharField",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child4>is_abstract:False",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child4>custom_queryset:djangoexample.exampleapp.models.Child4QuerySet",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child4>mro_0:djangoexample.exampleapp.models.Parent2",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child4>mro_1:djangoexample.exampleapp.models.Parent",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child4>field:id",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child4>field:id>field_type:django.db.models.fields.BigAutoField",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child4>field:one",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child4>field:one>field_type:django.db.models.fields.CharField",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child4>field:two",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child4>field:two>field_type:django.db.models.fields.CharField",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child4>field:three",
            "module:djangoexample.exampleapp.models>model:djangoexample.exampleapp.models.Child4>field:three>field_type:django.db.models.fields.CharField",
        ]

        virtual_dependency = virtual_dependencies.VirtualDependency.create(
            discovered_project=discovered_django_example,
            module=module,
            virtual_dependency_namer=Namer(),
        )

        all_models = discovered_django_example.all_models

        assert virtual_dependency == virtual_dependencies.VirtualDependency(
            module=module,
            summary=virtual_dependencies.VirtualDependencySummary(
                virtual_namespace=ImportPath("__virtual__"),
                virtual_import_path=ImportPath("__virtual__.mod_djangoexample_exampleapp_models"),
                module_import_path=module.import_path,
                significant_info=significant_info,
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

    def test_significant_info_takes_into_account_field_related_model(
        self, discovered_django_example: protocols.Discovered[Project]
    ) -> None:
        import djangoexample.relations1.models

        module = discovered_django_example.installed_models_modules[
            ImportPath.from_module(djangoexample.relations1.models)
        ]

        virtual_dependency = virtual_dependencies.VirtualDependency.create(
            discovered_project=discovered_django_example,
            module=module,
            virtual_dependency_namer=Namer(),
        )

        assert virtual_dependency.summary.significant_info == [
            "module:djangoexample.relations1.models",
            "module:djangoexample.relations1.models>concrete:djangoexample.relations1.models.Abstract=djangoexample.relations1.models.Child1,djangoexample.relations1.models.Child2",
            "module:djangoexample.relations1.models>concrete:djangoexample.relations1.models.Child1=djangoexample.relations1.models.Child1",
            "module:djangoexample.relations1.models>concrete:djangoexample.relations1.models.Child2=djangoexample.relations1.models.Child2",
            "module:djangoexample.relations1.models>concrete:djangoexample.relations1.models.Concrete1=djangoexample.relations1.models.Concrete1",
            "module:djangoexample.relations1.models>concrete:djangoexample.relations1.models.Concrete2=djangoexample.relations1.models.Concrete2",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Abstract>is_abstract:True",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>is_abstract:False",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>custom_queryset:djangoexample.relations1.models.Child1QuerySet",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>mro_0:djangoexample.relations1.models.Abstract",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>field:Concrete2_children+",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>field:Concrete2_children+>field_type:django.db.models.fields.reverse_related.ManyToOneRel",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>field:children",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>field:children>field_type:django.db.models.fields.reverse_related.ManyToManyRel",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>field:children>related_model:djangoexample.relations1.models.Concrete2",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>field:id",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child1>field:id>field_type:django.db.models.fields.BigAutoField",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child2>is_abstract:False",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child2>mro_0:djangoexample.relations1.models.Abstract",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child2>field:id",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Child2>field:id>field_type:django.db.models.fields.BigAutoField",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>is_abstract:False",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>custom_queryset:djangoexample.relations1.models.Concrete1QuerySet",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>field:c2s",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>field:c2s>field_type:django.db.models.fields.reverse_related.ManyToOneRel",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>field:c2s>related_model:djangoexample.relations1.models.Concrete2",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>field:thing",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>field:thing>field_type:django.db.models.fields.reverse_related.OneToOneRel",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>field:thing>related_model:djangoexample.relations2.models.Thing",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>field:id",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete1>field:id>field_type:django.db.models.fields.BigAutoField",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>is_abstract:False",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:Concrete2_children+",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:Concrete2_children+>field_type:django.db.models.fields.reverse_related.ManyToOneRel",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:id",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:id>field_type:django.db.models.fields.BigAutoField",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:concrete1",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:concrete1>field_type:django.db.models.fields.related.ForeignKey",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:concrete1>related_model:djangoexample.relations1.models.Concrete1",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:children",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:children>field_type:django.db.models.fields.related.ManyToManyField",
            "module:djangoexample.relations1.models>model:djangoexample.relations1.models.Concrete2>field:children>related_model:djangoexample.relations1.models.Child1",
        ]
