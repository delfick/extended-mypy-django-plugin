import functools
import os
import pathlib

import pytest

from extended_mypy_django_plugin.django_analysis import (
    ImportPath,
    Project,
    protocols,
    virtual_dependencies,
)
from extended_mypy_django_plugin.version import VERSION

here = pathlib.Path(__file__).parent


def make_report(
    *,
    concrete_annotations: dict[str, str],
    concrete_querysets: dict[str, str],
    report_import_path: dict[str, str],
) -> virtual_dependencies.Report:
    """
    Helper to make the tests below easier to read
    """
    return virtual_dependencies.Report(
        concrete_annotations={
            ImportPath(k): ImportPath(v) for k, v in concrete_annotations.items()
        },
        concrete_querysets={ImportPath(k): ImportPath(v) for k, v in concrete_querysets.items()},
        report_import_path={ImportPath(k): ImportPath(v) for k, v in report_import_path.items()},
    )


class TestEnd2End:
    def test_works(
        self,
        tmp_path_factory: pytest.TempPathFactory,
        discovered_django_example: protocols.Discovered[Project],
    ) -> None:
        count: int = 0

        class VirtualDependencyHandler(
            virtual_dependencies.VirtualDependencyHandler[
                Project,
                virtual_dependencies.VirtualDependency[Project],
                virtual_dependencies.Report,
            ]
        ):
            @classmethod
            def make_project(
                cls, *, project_root: pathlib.Path, django_settings_module: str
            ) -> Project:
                raise NotImplementedError()

            def interface_differentiator(self) -> str:
                nonlocal count
                count += 1
                return f"__differentiated__{count}"

            def get_virtual_namespace(self) -> protocols.ImportPath:
                return ImportPath("__virtual__")

            def hash_installed_apps(self) -> str:
                return "__installed_apps_hash__"

            def make_report_factory(
                self, *, installed_apps_hash: str
            ) -> protocols.ReportFactory[
                virtual_dependencies.VirtualDependency[Project], virtual_dependencies.Report
            ]:
                return virtual_dependencies.make_report_factory(
                    hasher=self.hasher,
                    report_maker=virtual_dependencies.Report,
                    installed_apps_hash=installed_apps_hash,
                    make_differentiator=self.interface_differentiator,
                )

            def virtual_dependency_maker(
                self, *, virtual_dependency_namer: protocols.VirtualDependencyNamer
            ) -> protocols.VirtualDependencyMaker[
                Project, virtual_dependencies.VirtualDependency[Project]
            ]:
                return functools.partial(
                    virtual_dependencies.VirtualDependency.create,
                    discovered_project=self.discovered,
                    virtual_dependency_namer=virtual_dependency_namer,
                )

        destination = tmp_path_factory.mktemp("destination")

        handler = VirtualDependencyHandler(
            discovered=discovered_django_example, hasher=VirtualDependencyHandler.make_hasher()
        )

        report = handler.make_report(virtual_deps_destination=destination)

        assert (
            report.version
            == f"__virtual__|plugin:{VERSION}:installed_apps:__installed_apps_hash__|settings_types:2183014887|written_deps:917076629"
        )
        assert report.report == make_report(
            concrete_annotations={
                "django.contrib.admin.models.LogEntry": "__virtual__.mod_2456226428.Concrete__LogEntry",
                "django.contrib.auth.models.AbstractUser": "__virtual__.mod_2289830437.Concrete__AbstractUser",
                "django.contrib.auth.models.PermissionsMixin": "__virtual__.mod_2289830437.Concrete__PermissionsMixin",
                "django.contrib.auth.models.Permission": "__virtual__.mod_2289830437.Concrete__Permission",
                "django.contrib.auth.models.Group": "__virtual__.mod_2289830437.Concrete__Group",
                "django.contrib.auth.models.User": "__virtual__.mod_2289830437.Concrete__User",
                "django.contrib.contenttypes.models.ContentType": "__virtual__.mod_3961720227.Concrete__ContentType",
                "django.contrib.sessions.models.Session": "__virtual__.mod_3074165738.Concrete__Session",
                "djangoexample.exampleapp.models.Parent": "__virtual__.mod_3347844205.Concrete__Parent",
                "djangoexample.exampleapp.models.Parent2": "__virtual__.mod_3347844205.Concrete__Parent2",
                "djangoexample.exampleapp.models.Child1": "__virtual__.mod_3347844205.Concrete__Child1",
                "djangoexample.exampleapp.models.Child2": "__virtual__.mod_3347844205.Concrete__Child2",
                "djangoexample.exampleapp.models.Child3": "__virtual__.mod_3347844205.Concrete__Child3",
                "djangoexample.exampleapp.models.Child4": "__virtual__.mod_3347844205.Concrete__Child4",
                "djangoexample.exampleapp2.models.ChildOther": "__virtual__.mod_3537308831.Concrete__ChildOther",
                "djangoexample.exampleapp2.models.ChildOther2": "__virtual__.mod_3537308831.Concrete__ChildOther2",
                "djangoexample.relations1.models.Abstract": "__virtual__.mod_3327724610.Concrete__Abstract",
                "djangoexample.relations1.models.Child1": "__virtual__.mod_3327724610.Concrete__Child1",
                "djangoexample.relations1.models.Child2": "__virtual__.mod_3327724610.Concrete__Child2",
                "djangoexample.relations1.models.Concrete1": "__virtual__.mod_3327724610.Concrete__Concrete1",
                "djangoexample.relations1.models.Concrete2": "__virtual__.mod_3327724610.Concrete__Concrete2",
                "djangoexample.relations2.models.Thing": "__virtual__.mod_3328248899.Concrete__Thing",
                "djangoexample.only_abstract.models.AnAbstract": "__virtual__.mod_4035906997.Concrete__AnAbstract",
                "django.contrib.auth.base_user.AbstractBaseUser": "__virtual__.mod_2833058650.Concrete__AbstractBaseUser",
                "django.contrib.sessions.base_session.AbstractBaseSession": "__virtual__.mod_113708644.Concrete__AbstractBaseSession",
            },
            concrete_querysets={
                "django.contrib.admin.models.LogEntry": "__virtual__.mod_2456226428.ConcreteQuerySet__LogEntry",
                "django.contrib.auth.models.AbstractUser": "__virtual__.mod_2289830437.ConcreteQuerySet__AbstractUser",
                "django.contrib.auth.models.PermissionsMixin": "__virtual__.mod_2289830437.ConcreteQuerySet__PermissionsMixin",
                "django.contrib.auth.models.Permission": "__virtual__.mod_2289830437.ConcreteQuerySet__Permission",
                "django.contrib.auth.models.Group": "__virtual__.mod_2289830437.ConcreteQuerySet__Group",
                "django.contrib.auth.models.User": "__virtual__.mod_2289830437.ConcreteQuerySet__User",
                "django.contrib.contenttypes.models.ContentType": "__virtual__.mod_3961720227.ConcreteQuerySet__ContentType",
                "django.contrib.sessions.models.Session": "__virtual__.mod_3074165738.ConcreteQuerySet__Session",
                "djangoexample.exampleapp.models.Parent": "__virtual__.mod_3347844205.ConcreteQuerySet__Parent",
                "djangoexample.exampleapp.models.Parent2": "__virtual__.mod_3347844205.ConcreteQuerySet__Parent2",
                "djangoexample.exampleapp.models.Child1": "__virtual__.mod_3347844205.ConcreteQuerySet__Child1",
                "djangoexample.exampleapp.models.Child2": "__virtual__.mod_3347844205.ConcreteQuerySet__Child2",
                "djangoexample.exampleapp.models.Child3": "__virtual__.mod_3347844205.ConcreteQuerySet__Child3",
                "djangoexample.exampleapp.models.Child4": "__virtual__.mod_3347844205.ConcreteQuerySet__Child4",
                "djangoexample.exampleapp2.models.ChildOther": "__virtual__.mod_3537308831.ConcreteQuerySet__ChildOther",
                "djangoexample.exampleapp2.models.ChildOther2": "__virtual__.mod_3537308831.ConcreteQuerySet__ChildOther2",
                "djangoexample.relations1.models.Abstract": "__virtual__.mod_3327724610.ConcreteQuerySet__Abstract",
                "djangoexample.relations1.models.Child1": "__virtual__.mod_3327724610.ConcreteQuerySet__Child1",
                "djangoexample.relations1.models.Child2": "__virtual__.mod_3327724610.ConcreteQuerySet__Child2",
                "djangoexample.relations1.models.Concrete1": "__virtual__.mod_3327724610.ConcreteQuerySet__Concrete1",
                "djangoexample.relations1.models.Concrete2": "__virtual__.mod_3327724610.ConcreteQuerySet__Concrete2",
                "djangoexample.relations2.models.Thing": "__virtual__.mod_3328248899.ConcreteQuerySet__Thing",
                "djangoexample.only_abstract.models.AnAbstract": "__virtual__.mod_4035906997.ConcreteQuerySet__AnAbstract",
                "django.contrib.auth.base_user.AbstractBaseUser": "__virtual__.mod_2833058650.ConcreteQuerySet__AbstractBaseUser",
                "django.contrib.sessions.base_session.AbstractBaseSession": "__virtual__.mod_113708644.ConcreteQuerySet__AbstractBaseSession",
            },
            report_import_path={
                "django.contrib.admin.models": "__virtual__.mod_2456226428",
                "django.contrib.auth.models": "__virtual__.mod_2289830437",
                "django.contrib.contenttypes.models": "__virtual__.mod_3961720227",
                "django.contrib.sessions.models": "__virtual__.mod_3074165738",
                "djangoexample.exampleapp.models": "__virtual__.mod_3347844205",
                "djangoexample.exampleapp2.models": "__virtual__.mod_3537308831",
                "djangoexample.relations1.models": "__virtual__.mod_3327724610",
                "djangoexample.relations2.models": "__virtual__.mod_3328248899",
                "djangoexample.only_abstract.models": "__virtual__.mod_4035906997",
                "djangoexample.empty_models.models": "__virtual__.mod_3808300370",
                "django.contrib.auth.base_user": "__virtual__.mod_2833058650",
                "django.contrib.sessions.base_session": "__virtual__.mod_113708644",
            },
        )

        assert len(list(destination.iterdir())) != 0

        found: dict[pathlib.Path, str] = {}
        expected: dict[pathlib.Path, str] = {}

        for path, result in ((destination, found), (here / "generated_reports", expected)):
            for root, _, files in os.walk(path):
                for name in files:
                    location = pathlib.Path(root) / name
                    result[location.relative_to(path)] = location.read_text()

        assert found == expected

        location = destination / handler.get_virtual_namespace() / "mod_3734901629.py"
        assert not location.exists()
        report.ensure_virtual_dependency(
            module_import_path="djangoexample.not_installed_with_concrete.models"
        )
        assert (
            location.read_text()
            == 'mod = "djangoexample.not_installed_with_concrete.models"\nsummary = "||not_installed||"\n'
        )

        assert (
            virtual_dependencies.VirtualDependencyScribe.get_report_summary(location)
            == "||not_installed||"
        )
