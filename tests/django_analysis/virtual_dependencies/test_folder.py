import functools
from collections.abc import Iterator

from extended_mypy_django_plugin.django_analysis import (
    ImportPath,
    Project,
    adler32_hash,
    protocols,
    virtual_dependencies,
)


class TestVirtualDependencyGenerator:
    def test_it_can_generate_virtual_dependencies(
        self, discovered_django_example: protocols.Discovered[Project]
    ) -> None:
        installed_apps_hash = "__hashed_installed_apps__"

        class CustomVirtualDependency(virtual_dependencies.VirtualDependency[Project]):
            @classmethod
            def find_significant_info_from_module(
                cls,
                *,
                discovered_project: protocols.Discovered[Project],
                module: protocols.Module,
                concrete_models: protocols.ConcreteModelsMap,
            ) -> Iterator[str]:
                yield f"__significant__{module.import_path}__"

        virtual_dependency_maker = functools.partial(
            CustomVirtualDependency.create,
            virtual_dependency_namer=virtual_dependencies.VirtualDependencyNamer(
                namespace="__virtual__", hasher=adler32_hash
            ),
            installed_apps_hash=installed_apps_hash,
            make_differentiator=lambda: "__differentiated__",
        )

        generated = virtual_dependencies.VirtualDependencyGenerator(
            virtual_dependency_maker=virtual_dependency_maker
        )(discovered_project=discovered_django_example)

        def IsModule(import_path: str) -> protocols.Module:
            return discovered_django_example.installed_models_modules[ImportPath(import_path)]

        def IsModel(import_path: str) -> protocols.Model:
            return discovered_django_example.all_models[ImportPath(import_path)]

        assert generated == {
            ImportPath("django.contrib.admin.models"): CustomVirtualDependency(
                module=IsModule("django.contrib.admin.models"),
                interface_differentiator="__differentiated__",
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_dependency_name=ImportPath("__virtual__.mod_2456226428"),
                    module_import_path=ImportPath("django.contrib.admin.models"),
                    installed_apps_hash="__hashed_installed_apps__",
                    significant_info=["__significant__django.contrib.admin.models__"],
                ),
                all_related_models=[
                    ImportPath("django.contrib.admin.models.LogEntry"),
                    ImportPath("django.contrib.auth.models.User"),
                    ImportPath("django.contrib.contenttypes.models.ContentType"),
                ],
                concrete_models={
                    ImportPath("django.contrib.admin.models.LogEntry"): [
                        IsModel("django.contrib.admin.models.LogEntry")
                    ]
                },
            ),
            ImportPath("django.contrib.auth.base_user"): CustomVirtualDependency(
                module=IsModule("django.contrib.auth.base_user"),
                interface_differentiator="__differentiated__",
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_dependency_name=ImportPath("__virtual__.mod_2833058650"),
                    module_import_path=ImportPath("django.contrib.auth.base_user"),
                    installed_apps_hash="__hashed_installed_apps__",
                    significant_info=["__significant__django.contrib.auth.base_user__"],
                ),
                all_related_models=[
                    ImportPath("django.contrib.auth.base_user.AbstractBaseUser"),
                ],
                concrete_models={
                    ImportPath("django.contrib.auth.base_user.AbstractBaseUser"): [
                        IsModel("django.contrib.auth.models.User")
                    ],
                },
            ),
            ImportPath("django.contrib.auth.models"): CustomVirtualDependency(
                module=IsModule("django.contrib.auth.models"),
                interface_differentiator="__differentiated__",
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_dependency_name=ImportPath("__virtual__.mod_2289830437"),
                    module_import_path=ImportPath("django.contrib.auth.models"),
                    installed_apps_hash="__hashed_installed_apps__",
                    significant_info=["__significant__django.contrib.auth.models__"],
                ),
                all_related_models=[
                    ImportPath("django.contrib.admin.models.LogEntry"),
                    ImportPath("django.contrib.auth.models.AbstractUser"),
                    ImportPath("django.contrib.auth.models.Group"),
                    ImportPath("django.contrib.auth.models.Permission"),
                    ImportPath("django.contrib.auth.models.PermissionsMixin"),
                    ImportPath("django.contrib.auth.models.User"),
                    ImportPath("django.contrib.contenttypes.models.ContentType"),
                ],
                concrete_models={
                    ImportPath("django.contrib.auth.models.AbstractUser"): [
                        IsModel("django.contrib.auth.models.User")
                    ],
                    ImportPath("django.contrib.auth.models.Group"): [
                        IsModel("django.contrib.auth.models.Group")
                    ],
                    ImportPath("django.contrib.auth.models.Permission"): [
                        IsModel("django.contrib.auth.models.Permission")
                    ],
                    ImportPath("django.contrib.auth.models.PermissionsMixin"): [
                        IsModel("django.contrib.auth.models.User")
                    ],
                    ImportPath("django.contrib.auth.models.User"): [
                        IsModel("django.contrib.auth.models.User")
                    ],
                },
            ),
            ImportPath("django.contrib.contenttypes.models"): CustomVirtualDependency(
                module=IsModule("django.contrib.contenttypes.models"),
                interface_differentiator="__differentiated__",
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_dependency_name=ImportPath("__virtual__.mod_3961720227"),
                    module_import_path=ImportPath("django.contrib.contenttypes.models"),
                    installed_apps_hash="__hashed_installed_apps__",
                    significant_info=["__significant__django.contrib.contenttypes.models__"],
                ),
                all_related_models=[
                    ImportPath("django.contrib.admin.models.LogEntry"),
                    ImportPath("django.contrib.auth.models.Permission"),
                    ImportPath("django.contrib.contenttypes.models.ContentType"),
                ],
                concrete_models={
                    ImportPath("django.contrib.contenttypes.models.ContentType"): [
                        IsModel("django.contrib.contenttypes.models.ContentType")
                    ]
                },
            ),
            ImportPath("django.contrib.sessions.base_session"): CustomVirtualDependency(
                module=IsModule("django.contrib.sessions.base_session"),
                interface_differentiator="__differentiated__",
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_dependency_name=ImportPath("__virtual__.mod_113708644"),
                    module_import_path=ImportPath("django.contrib.sessions.base_session"),
                    installed_apps_hash="__hashed_installed_apps__",
                    significant_info=["__significant__django.contrib.sessions.base_session__"],
                ),
                all_related_models=[
                    ImportPath("django.contrib.sessions.base_session.AbstractBaseSession"),
                ],
                concrete_models={
                    ImportPath("django.contrib.sessions.base_session.AbstractBaseSession"): [
                        IsModel("django.contrib.sessions.models.Session")
                    ]
                },
            ),
            ImportPath("django.contrib.sessions.models"): CustomVirtualDependency(
                module=IsModule("django.contrib.sessions.models"),
                interface_differentiator="__differentiated__",
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_dependency_name=ImportPath("__virtual__.mod_3074165738"),
                    module_import_path=ImportPath("django.contrib.sessions.models"),
                    installed_apps_hash="__hashed_installed_apps__",
                    significant_info=["__significant__django.contrib.sessions.models__"],
                ),
                all_related_models=[
                    ImportPath("django.contrib.sessions.models.Session"),
                ],
                concrete_models={
                    ImportPath("django.contrib.sessions.models.Session"): [
                        IsModel("django.contrib.sessions.models.Session")
                    ],
                },
            ),
            ImportPath("djangoexample.exampleapp.models"): CustomVirtualDependency(
                module=IsModule("djangoexample.exampleapp.models"),
                interface_differentiator="__differentiated__",
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_dependency_name=ImportPath("__virtual__.mod_3347844205"),
                    module_import_path=ImportPath("djangoexample.exampleapp.models"),
                    installed_apps_hash="__hashed_installed_apps__",
                    significant_info=["__significant__djangoexample.exampleapp.models__"],
                ),
                all_related_models=[
                    ImportPath("djangoexample.exampleapp.models.Child1"),
                    ImportPath("djangoexample.exampleapp.models.Child2"),
                    ImportPath("djangoexample.exampleapp.models.Child3"),
                    ImportPath("djangoexample.exampleapp.models.Child4"),
                    ImportPath("djangoexample.exampleapp.models.Parent"),
                    ImportPath("djangoexample.exampleapp.models.Parent2"),
                ],
                concrete_models={
                    ImportPath("djangoexample.exampleapp.models.Child1"): [
                        IsModel("djangoexample.exampleapp.models.Child1"),
                    ],
                    ImportPath("djangoexample.exampleapp.models.Child2"): [
                        IsModel("djangoexample.exampleapp.models.Child2")
                    ],
                    ImportPath("djangoexample.exampleapp.models.Child3"): [
                        IsModel("djangoexample.exampleapp.models.Child3")
                    ],
                    ImportPath("djangoexample.exampleapp.models.Child4"): [
                        IsModel("djangoexample.exampleapp.models.Child4")
                    ],
                    ImportPath("djangoexample.exampleapp.models.Parent"): [
                        IsModel("djangoexample.exampleapp.models.Child1"),
                        IsModel("djangoexample.exampleapp.models.Child2"),
                        IsModel("djangoexample.exampleapp.models.Child3"),
                        IsModel("djangoexample.exampleapp.models.Child4"),
                        IsModel("djangoexample.exampleapp2.models.ChildOther"),
                        IsModel("djangoexample.exampleapp2.models.ChildOther2"),
                    ],
                    ImportPath("djangoexample.exampleapp.models.Parent2"): [
                        IsModel("djangoexample.exampleapp.models.Child3"),
                        IsModel("djangoexample.exampleapp.models.Child4"),
                    ],
                },
            ),
            ImportPath("djangoexample.exampleapp2.models"): CustomVirtualDependency(
                module=IsModule("djangoexample.exampleapp2.models"),
                interface_differentiator="__differentiated__",
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_dependency_name=ImportPath("__virtual__.mod_3537308831"),
                    module_import_path=ImportPath("djangoexample.exampleapp2.models"),
                    installed_apps_hash="__hashed_installed_apps__",
                    significant_info=["__significant__djangoexample.exampleapp2.models__"],
                ),
                all_related_models=[
                    ImportPath("djangoexample.exampleapp2.models.ChildOther"),
                    ImportPath("djangoexample.exampleapp2.models.ChildOther2"),
                ],
                concrete_models={
                    ImportPath("djangoexample.exampleapp2.models.ChildOther"): [
                        IsModel("djangoexample.exampleapp2.models.ChildOther")
                    ],
                    ImportPath("djangoexample.exampleapp2.models.ChildOther2"): [
                        IsModel("djangoexample.exampleapp2.models.ChildOther2"),
                    ],
                },
            ),
            ImportPath("djangoexample.only_abstract.models"): CustomVirtualDependency(
                module=IsModule("djangoexample.only_abstract.models"),
                interface_differentiator="__differentiated__",
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_dependency_name=ImportPath("__virtual__.mod_4035906997"),
                    module_import_path=ImportPath("djangoexample.only_abstract.models"),
                    installed_apps_hash="__hashed_installed_apps__",
                    significant_info=["__significant__djangoexample.only_abstract.models__"],
                ),
                all_related_models=[
                    ImportPath("djangoexample.only_abstract.models.AnAbstract"),
                ],
                concrete_models={
                    ImportPath("djangoexample.only_abstract.models.AnAbstract"): [],
                },
            ),
            ImportPath("djangoexample.relations1.models"): CustomVirtualDependency(
                module=IsModule("djangoexample.relations1.models"),
                interface_differentiator="__differentiated__",
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_dependency_name=ImportPath("__virtual__.mod_3327724610"),
                    module_import_path=ImportPath("djangoexample.relations1.models"),
                    installed_apps_hash="__hashed_installed_apps__",
                    significant_info=["__significant__djangoexample.relations1.models__"],
                ),
                all_related_models=[
                    ImportPath("djangoexample.relations1.models.Abstract"),
                    ImportPath("djangoexample.relations1.models.Child1"),
                    ImportPath("djangoexample.relations1.models.Child2"),
                    ImportPath("djangoexample.relations1.models.Concrete1"),
                    ImportPath("djangoexample.relations1.models.Concrete2"),
                    ImportPath("djangoexample.relations2.models.Thing"),
                ],
                concrete_models={
                    ImportPath("djangoexample.relations1.models.Abstract"): [
                        IsModel("djangoexample.relations1.models.Child1"),
                        IsModel("djangoexample.relations1.models.Child2"),
                    ],
                    ImportPath("djangoexample.relations1.models.Child1"): [
                        IsModel("djangoexample.relations1.models.Child1"),
                    ],
                    ImportPath("djangoexample.relations1.models.Child2"): [
                        IsModel("djangoexample.relations1.models.Child2"),
                    ],
                    ImportPath("djangoexample.relations1.models.Concrete1"): [
                        IsModel("djangoexample.relations1.models.Concrete1"),
                    ],
                    ImportPath("djangoexample.relations1.models.Concrete2"): [
                        IsModel("djangoexample.relations1.models.Concrete2"),
                    ],
                },
            ),
            ImportPath("djangoexample.relations2.models"): CustomVirtualDependency(
                module=IsModule("djangoexample.relations2.models"),
                interface_differentiator="__differentiated__",
                summary=virtual_dependencies.VirtualDependencySummary(
                    virtual_dependency_name=ImportPath("__virtual__.mod_3328248899"),
                    module_import_path=ImportPath("djangoexample.relations2.models"),
                    installed_apps_hash="__hashed_installed_apps__",
                    significant_info=["__significant__djangoexample.relations2.models__"],
                ),
                all_related_models=[
                    ImportPath("djangoexample.relations1.models.Concrete1"),
                    ImportPath("djangoexample.relations2.models.Thing"),
                ],
                concrete_models={
                    ImportPath("djangoexample.relations2.models.Thing"): [
                        IsModel("djangoexample.relations2.models.Thing")
                    ],
                },
            ),
        }
